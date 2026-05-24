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
INIT_WAIT = 3.0
PAGE_WAIT = 2.0
LOGIN_TIMEOUT = 120
PAGE_LOAD_TIMEOUT = 30

if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(__file__))
PROFILE_DIR = os.path.join(_BASE, 'data', 'chrome_profile')


def scrape_jd(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """京东爬虫主入口"""
    page = None
    products = []
    seen_skus = set()
    page_num = 1

    try:
        if message_callback:
            message_callback('>>> from crawler.jd_crawler import scrape_jd')

        co = _create_options()
        co.headless(False)

        # 使用固定目录保存登录状态
        os.makedirs(PROFILE_DIR, exist_ok=True)
        co.set_argument(f'--user-data-dir={PROFILE_DIR}')

        if message_callback:
            message_callback('>>> page = ChromiumPage(options)')
        page = _create_page(co)
        page.set.load_mode('eager')  # 修复：使用方法调用形式

        base_url = _clean_jd_url(url or 'https://search.jd.com/Search?keyword=手机')

        # 加载首页
        page_url = _build_jd_page_url(base_url, page_num)
        if message_callback:
            message_callback(f'>>> page.get("{page_url[:50]}...")')

        try:
            page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
        except Exception as e:
            if message_callback:
                message_callback('>>> # 页面加载超时，继续尝试...')
            logger.warning(f'页面加载超时: {e}')

        time.sleep(INIT_WAIT)

        # 检查是否被反爬虫拦截
        current_url = page.url or ''
        retry_count = 0
        max_retries = 3

        while ('risk_handler' in current_url or 'cfe.m.jd.com' in current_url) and retry_count < max_retries:
            retry_count += 1
            if message_callback:
                message_callback(f'>>> # 检测到反爬虫，重试 {retry_count}/{max_retries}')

            time.sleep(3)
            try:
                page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                time.sleep(3)
            except:
                pass
            current_url = page.url or ''

        if 'risk_handler' in current_url or 'cfe.m.jd.com' in current_url:
            if message_callback:
                message_callback('>>> # 无法绕过反爬虫，建议手动登录后重试')
            logger.error('京东反爬虫拦截')
            return []

        # 检查登录
        current_url = page.url or ''
        if 'passport.jd.com' in current_url or 'login' in current_url.lower():
            if message_callback:
                message_callback('>>> # 需要登录，请在浏览器窗口中登录（120秒内）')
            if not _wait_for_login(page, stop_check):
                if message_callback:
                    message_callback('>>> # 登录超时或取消')
                return []
            if message_callback:
                message_callback('>>> # 登录成功，继续访问...')
            try:
                page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                time.sleep(2)
            except Exception as e:
                logger.warning(f'重新加载页面失败: {e}')

        # 开始采集
        if message_callback:
            message_callback('>>> # 开始采集商品数据...')

        # 翻页爬取
        while len(products) < count and page_num <= 10:
            if stop_check and stop_check():
                if message_callback:
                    message_callback('>>> break  # 用户取消')
                break

            try:
                # 修复：使用更精确的选择器
                try:
                    page.wait.ele_displayed('css:#J_goodsList li[data-sku]', timeout=10)
                except Exception as e:
                    # 备用选择器
                    try:
                        page.wait.ele_displayed('css:li.gl-item[data-sku]', timeout=5)
                    except:
                        logger.warning(f'等待商品列表超时: {e}')
                        if message_callback:
                            message_callback(f'>>> # 未找到商品，尝试下一页...')
                        page_num += 2
                        if page_num <= 10:
                            next_url = _build_jd_page_url(base_url, page_num)
                            try:
                                page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                            except Exception:
                                pass
                            time.sleep(PAGE_WAIT)
                        continue

                time.sleep(1.0)  # 增加等待时间

                # 修复：使用更精确的选择器
                cards = page.eles('css:#J_goodsList li[data-sku]')
                if not cards:
                    cards = page.eles('css:li.gl-item[data-sku]')
                if not cards:
                    cards = page.eles('css:[data-sku]')

                if not cards:
                    logger.warning(f'未找到商品卡片')
                    break

                if message_callback:
                    message_callback(f'>>> cards = page.eles(...)  # {len(cards)} 个商品')

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
                            if message_callback:
                                name_short = product['name'][:20] + "..." if len(product['name']) > 20 else product['name']
                                price = product.get('price', 0)
                                message_callback(f'>>> products.append({{"name": "{name_short}", "price": {price}}})  # #{len(products)}')
                    except Exception as e:
                        logger.debug(f'提取商品失败: {e}')
                        continue

                # 翻到下一页
                page_num += 2
                if len(products) < count:
                    next_url = _build_jd_page_url(base_url, page_num)
                    if message_callback:
                        message_callback(f'>>> page.get(...)  # 第 {page_num} 页')
                    try:
                        page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                    except Exception as e:
                        logger.warning(f'翻页超时: {e}')
                    time.sleep(PAGE_WAIT)

            except Exception as e:
                logger.error(f'页面操作出错: {e}')
                if message_callback:
                    message_callback(f'>>> # 采集出错: {str(e)[:30]}')
                break

        if message_callback:
            message_callback(f'>>> return products  # 共 {len(products)} 条')

        return products[:count]

    except Exception as e:
        logger.error(f'京东采集出错: {e}')
        if message_callback:
            message_callback(f'>>> raise Exception("{str(e)[:50]}")')
        return products
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def _extract_jd(card):
    """从京东 React 卡片提取数据"""
    data = {}

    # SKU & URL
    sku = card.attr('data-sku') or ''
    data['product_url'] = f'https://item.jd.com/{sku}.html' if sku else ''

    # 修复：增强标题提取
    title_el = card.ele('css:a[title]') or card.ele('css:.p-name em') or card.ele('css:span[title]')
    if title_el:
        data['name'] = (title_el.attr('title') or title_el.text or '').strip()
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

    # 修复：销量解析
    data['comment_count'] = 0
    card_text = card.text or ''
    m = re.search(r'(\d+\.?\d*)\s*([万亿]?)\+?\s*(人已买|人加购|条评价)', card_text)
    if m:
        num_str = m.group(1)
        unit = m.group(2)
        multiplier = 1
        if unit == '万':
            multiplier = 10000
        elif unit == '亿':
            multiplier = 100000000
        try:
            data['comment_count'] = int(float(num_str) * multiplier)
        except:
            data['comment_count'] = 0

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
            current_url = page.url or ''
            if 'passport.jd.com' not in current_url and 'login' not in current_url.lower():
                if 'search.jd.com' in current_url or 'list.jd.com' in current_url or 'jd.com' in current_url:
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

    # 设置 Edge 浏览器路径
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--window-size=1280,900')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-extensions')
    co.set_argument('--mute-audio')

    # 反反爬配置
    co.set_argument('--disable-web-security')
    co.set_argument('--allow-running-insecure-content')
    co.set_argument('--disable-features=IsolateOrigins,site-per-process')

    # 添加真实的 User-Agent
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

    return co


def _create_page(co):
    """创建浏览器页面"""
    from DrissionPage import ChromiumPage
    return ChromiumPage(addr_or_opts=co)  # 修复：使用关键字参数
