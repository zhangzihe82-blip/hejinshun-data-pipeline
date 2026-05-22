"""
京东爬虫子模块
支持 React 新版页面，需登录
"""
import re
import time
import os
import sys
import logging

logger = logging.getLogger(__name__)

# 配置参数
INIT_WAIT = 1.0
PAGE_WAIT = 1.0
LOGIN_TIMEOUT = 120

if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(__file__))
PROFILE_DIR = os.path.join(_BASE, 'data', 'chrome_profile')


def scrape_jd(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """京东爬虫主入口"""
    os.makedirs(PROFILE_DIR, exist_ok=True)

    co = _create_options()
    co.headless(False)
    co.set_argument(f'--user-data-dir={PROFILE_DIR}')

    page = _create_page(co)
    products = []
    seen_skus = set()
    page_num = 1

    try:
        base_url = _clean_jd_url(url or 'https://search.jd.com/Search?keyword=手机')

        # 加载首页
        page_url = _build_jd_page_url(base_url, page_num)
        page.get(page_url)
        time.sleep(2)

        # 检查登录
        if 'passport.jd.com' in page.url:
            if message_callback:
                message_callback('请在弹出的浏览器中登录京东账号（120秒内）')
            if not _wait_for_login(page, stop_check):
                if message_callback:
                    message_callback('登录超时，请重试')
                return []
            if message_callback:
                message_callback('登录成功，开始爬取...')
            page.get(page_url)
            time.sleep(2)

        # 翻页爬取
        while len(products) < count and page_num <= 10:
            if stop_check and stop_check():
                break

            page.wait.ele_displayed('css:[data-sku]', timeout=8)
            time.sleep(0.3)

            cards = page.eles('css:[data-sku]')
            prev_count = len(products)

            for card in cards:
                if len(products) >= count:
                    break
                if stop_check and stop_check():
                    break
                try:
                    product = _extract_jd(card)
                    sku = card.attr('data-sku') or ''
                    if product and product['name'] and sku not in seen_skus:
                        seen_skus.add(sku)
                        products.append(product)
                        if progress_callback:
                            progress_callback(len(products), count)
                except Exception:
                    continue

            if len(products) == prev_count:
                break

            # 翻到下一页
            page_num += 2
            if len(products) < count:
                next_url = _build_jd_page_url(base_url, page_num)
                page.get(next_url)
                time.sleep(PAGE_WAIT)

        return products[:count]

    finally:
        page.quit()


def _extract_jd(card):
    """从京东 React 卡片提取数据"""
    data = {}

    # SKU & URL
    sku = card.attr('data-sku') or ''
    data['product_url'] = f'https://item.jd.com/{sku}.html' if sku else ''

    # 标题
    title_el = card.ele('css:span[title]')
    if title_el:
        data['name'] = title_el.attr('title').strip()
    else:
        best = ''
        for s in card.eles('css:span'):
            t = s.text.strip()
            if len(t) > len(best):
                best = t
        data['name'] = best

    if not data.get('name'):
        return None

    # 价格
    data['price'] = 0
    for el in card.eles('css:[class*="_price_"]'):
        cls = el.attr('class') or ''
        if '_gray_' in cls or '_subsidy_' in cls:
            continue
        text = el.text.strip()
        m = re.search(r'(\d+\.?\d*)', text)
        if m:
            data['price'] = float(m.group(1))
            break

    # 原价
    data['original_price'] = None
    gray_el = card.ele('css:[class*="_gray_"]')
    if gray_el:
        m = re.search(r'(\d+\.?\d*)', gray_el.text)
        if m:
            data['original_price'] = float(m.group(1))

    # 图片
    data['image_url'] = ''
    for img in card.eles('css:img'):
        src = img.attr('src') or img.attr('data-src') or ''
        if src and ('360buyimg' in src or 'jd.com' in src) and 'icon' not in src.lower():
            data['image_url'] = src
            break
    if not data['image_url']:
        first_img = card.ele('css:img[src]')
        if first_img:
            data['image_url'] = first_img.attr('src') or ''

    # 店铺/平台
    if card.ele('css:img[alt="自营"]'):
        data['platform'] = '京东自营'
    else:
        data['platform'] = '京东'

    # 销量/评论
    data['comment_count'] = 0
    card_text = card.text or ''
    m = re.search(r'(\d+[万亿]?\+?)人已买', card_text)
    if not m:
        m = re.search(r'(\d+[万亿]?\+?)人加购', card_text)
    if not m:
        m = re.search(r'(\d+[万亿]?\+?)条评价', card_text)
    if m:
        s = m.group(1).replace('万', '0000').replace('亿', '00000000').replace('+', '')
        s = re.sub(r'[^\d]', '', s)
        if s:
            data['comment_count'] = int(s)

    data['rating'] = None
    data['category'] = '京东'
    return data


def _wait_for_login(page, stop_check, timeout=LOGIN_TIMEOUT):
    """等待用户登录京东"""
    start = time.time()
    while time.time() - start < timeout:
        if stop_check and stop_check():
            return False
        try:
            if 'passport.jd.com' not in page.url and ('search.jd.com' in page.url or 'list.jd.com' in page.url):
                return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def _clean_jd_url(url):
    """清理京东URL，保留关键参数"""
    from urllib.parse import urlparse
    keep = ['keyword', 'enc', 'wq', 'cat']
    parsed = urlparse(url)
    params = {}
    for pair in parsed.query.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            if k in keep:
                params[k] = v
    base = f'{parsed.scheme}://{parsed.netloc}{parsed.path}'
    if params:
        base += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return base


def _build_jd_page_url(base_url, page_num):
    """构建分页URL"""
    url = re.sub(r'[&?]page=\d+', '', base_url)
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}page={page_num}'


def _create_options():
    """创建浏览器选项"""
    from DrissionPage import ChromiumOptions
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--window-size=1280,900')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-extensions')
    co.set_argument('--mute-audio')
    return co


def _create_page(co):
    """创建浏览器页面"""
    from DrissionPage import ChromiumPage
    return ChromiumPage(co)
