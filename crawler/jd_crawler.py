"""
京东爬虫子模块
支持 React 新版页面，需登录
支持多种京东页面类型，自动适配选择器
完善的异常处理、备用方案与自动恢复机制
"""
import re
import time
import os
import sys
import logging
import traceback
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# 配置参数
INIT_WAIT = 1.0
PAGE_WAIT = 1.0
LOGIN_TIMEOUT = 120
PAGE_LOAD_TIMEOUT = 30
MAX_NETWORK_RETRIES = 3          # 网络超时重试次数
MAX_BROWSER_CRASH_RETRIES = 2    # 浏览器崩溃重启次数
MAX_ANTI_CRAWL_RETRIES = 3       # 反爬虫重试次数
PAGE_REFRESH_ON_BLANK = True     # 检测空白页自动刷新
CAPTCHA_WAIT_SECONDS = 30        # 验证码等待秒数
BLANK_PAGE_THRESHOLD = 200       # 页面内容低于此字符数视为空白

if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(__file__))
PROFILE_DIR = os.path.join(_BASE, 'data', 'chrome_profile')

# ── 不同页面类型的选择器配置 ──────────────────────────────────
PAGE_SELECTORS = {
    'search': {
        # 标准 search.jd.com 搜索页
        'card': 'css:[data-sku]',
        'title': 'css:span[title]',
        'sku_attr': 'data-sku',
        'price': 'css:[class*="_price_"]',
    },
    'list': {
        # list.jd.com 列表页
        'card': 'css:.gl-item',
        'title': 'css:.p-name a em',
        'sku_attr': 'data-sku',
        'price': 'css:.p-price i',
    },
    'item': {
        # item.jd.com 商品详情页 (单商品)
        'card': 'css:.product-intro, css:.itemInfo, css:#detail',
        'title': 'css:.itemInfo .sku-name, css:.product-intro .name, css:.sku-name',
        'sku_attr': 'data-sku',
        'price': 'css:.price .p-price, css:[class*="_price_"], css:.p-price i',
    },
    'mall': {
        # mall.jd.com 店铺页
        'card': 'css:[data-sku], css:.goods-item, css:.product-item, css:.jGoodsList li',
        'title': 'css:span[title], css:.p-name a em, css:.goods-name a',
        'sku_attr': 'data-sku',
        'price': 'css:[class*="_price_"], css:.p-price i, css:.goods-price',
    },
    're_jd': {
        # re.jd.com 短链接跳转页
        'card': 'css:[data-sku], css:.gl-item, css:.J-goods-list .goods-item',
        'title': 'css:span[title], css:.p-name a em, css:.goods-name',
        'sku_attr': 'data-sku',
        'price': 'css:[class*="_price_"], css:.p-price i, css:.goods-price',
    },
    'mobile': {
        # m.jd.com 移动端页面
        'card': 'css:.product-item, css:.search-result-item, css:[data-sku], css:.commodity-item',
        'title': 'css:.product-name, css:.p-name, css:span[title], css:.commodity-name',
        'sku_attr': 'data-sku',
        'price': 'css:.product-price, css:[class*="_price_"], css:.commodity-price',
    },
}

# ── 备用选择器 (主选择器全部失败时按序尝试) ────────────────────
FALLBACK_CARD_SELECTORS = [
    'css:[data-sku]',
    'css:.gl-item',
    'css:.goods-item',
    'css:.product-item',
    'css:.commodity-item',
    'css:.J-goods-list .goods-item',
    'css:[class*="goods"]',
    'css:[class*="product"]',
    'css:.search-result-item',
    'css:.jGoodsList li',
]

FALLBACK_TITLE_SELECTORS = [
    'css:span[title]',
    'css:.p-name a em',
    'css:.sku-name',
    'css:.product-name',
    'css:.goods-name',
    'css:.goods-name a',
    'css:.commodity-name',
    'css:.itemInfo .name',
    'css:a[title]',
]

FALLBACK_PRICE_SELECTORS = [
    'css:[class*="_price_"]',
    'css:.p-price i',
    'css:.product-price',
    'css:.goods-price',
    'css:.commodity-price',
    'css:strong[class*="price"]',
    'css:span[class*="price"]',
    'css:em[class*="price"]',
]


# ── 自动检测与恢复函数 ────────────────────────────────────────
def _is_blank_page(page):
    """检测页面是否空白"""
    try:
        body_text = page.ele('css:body').text or ''
        return len(body_text.strip()) < BLANK_PAGE_THRESHOLD
    except Exception:
        return True


def _is_captcha_page(page):
    """检测是否出现验证码页面"""
    try:
        captcha_selectors = [
            'css:#captcha',
            'css:.captcha',
            'css:[class*="captcha"]',
            'css:[class*="verify"]',
            'css:#JD_Verification1',
            'css:.verify-wrap',
        ]
        for sel in captcha_selectors:
            el = page.ele(sel, timeout=0.5)
            if el:
                return True
        return False
    except Exception:
        return False


def _is_login_expired(page):
    """检测登录是否过期"""
    try:
        current_url = page.url or ''
        # 被重定向到登录页
        if 'passport.jd.com' in current_url or 'login' in current_url.lower():
            return True
        # 检查登录过期提示
        expired_selectors = [
            'css:.login-expired',
            'css:[class*="login-tip"]',
            'css:.login-btn',
        ]
        for sel in expired_selectors:
            el = page.ele(sel, timeout=0.5)
            if el:
                return True
        return False
    except Exception:
        return False


def _is_anti_crawl(page):
    """检测是否被反爬虫拦截"""
    try:
        current_url = page.url or ''
        if 'risk_handler' in current_url or 'cfe.m.jd.com' in current_url:
            return True
        # 检测反爬虫页面元素
        anti_selectors = [
            'css:.risk-handler',
            'css:[class*="risk"]',
            'css:#risk_handler',
        ]
        for sel in anti_selectors:
            el = page.ele(sel, timeout=0.5)
            if el:
                return True
        return False
    except Exception:
        return False


def _detect_page_type(page, url):
    """检测页面类型，支持所有京东链接格式"""
    url = url or ''

    if 'list.jd.com' in url:
        return 'list'
    elif 'item.jd.com' in url:
        return 'item'
    elif 'mall.jd.com' in url:
        return 'mall'
    elif 're.jd.com' in url:
        return 're_jd'
    elif 'm.jd.com' in url:
        return 'mobile'

    # 根据页面元素检测
    try:
        if page.eles('css:[data-sku]'):
            # 进一步区分 search 和 mall
            if page.eles('css:.gl-item'):
                return 'list'
            return 'search'
        elif page.eles('css:.gl-item'):
            return 'list'
        elif page.eles('css:.product-intro') or page.eles('css:.itemInfo'):
            return 'item'
        elif page.eles('css:.J-goods-list .goods-item') or page.eles('css:.jGoodsList li'):
            return 'mall'
        elif page.eles('css:.product-item') or page.eles('css:.commodity-item'):
            return 'mobile'
    except Exception:
        pass

    return 'search'


# ── URL 处理 ──────────────────────────────────────────────────
def _clean_jd_url(url):
    """清理京东URL，保留关键参数

    支持所有京东链接格式:
    - search.jd.com/search?keyword=xxx
    - list.jd.com/list.html?cat=xxx
    - re.jd.com/xxx (短链接)
    - item.jd.com/xxx.html (商品详情页)
    - mall.jd.com/xxx (店铺页)
    - m.jd.com/xxx (移动端页面)
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    # re.jd.com 转换为 search.jd.com
    if 're.jd.com' in netloc:
        params = parse_qs(parsed.query)
        keyword = params.get('keyword', [''])[0]
        # 尝试从路径中提取关键词
        if not keyword:
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[0]:
                keyword = path_parts[0]
        if keyword:
            new_url = f'https://search.jd.com/Search?keyword={keyword}'
            logger.info(f'URL转换: {url} -> {new_url}')
            return new_url
        # 无法提取关键词，直接尝试访问
        return url

    # m.jd.com 移动端 -> 桌面端搜索
    if 'm.jd.com' in netloc:
        params = parse_qs(parsed.query)
        keyword = params.get('keyword', [''])[0]
        if not keyword:
            # 尝试从路径提取商品ID
            m = re.search(r'/product/(\d+)', parsed.path)
            if m:
                return f'https://item.jd.com/{m.group(1)}.html'
        if keyword:
            new_url = f'https://search.jd.com/Search?keyword={keyword}'
            logger.info(f'移动端URL转换: {url} -> {new_url}')
            return new_url
        return url

    # item.jd.com 商品详情页 - 保持原样
    if 'item.jd.com' in netloc:
        return url

    # mall.jd.com 店铺页 - 保持原样
    if 'mall.jd.com' in netloc:
        return url

    # 标准京东URL处理 (search.jd.com, list.jd.com)
    keep = ['keyword', 'enc', 'wq', 'cat']
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
    # item.jd.com 不支持分页
    if 'item.jd.com' in base_url:
        return base_url
    url = re.sub(r'[&?]page=\d+', '', base_url)
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}page={page_num}'


def _extract_sku_from_url(url):
    """从URL中提取SKU ID"""
    if not url:
        return None
    # item.jd.com/12345.html
    m = re.search(r'item\.jd\.com/(\d+)', url)
    if m:
        return m.group(1)
    # /product/12345
    m = re.search(r'/product/(\d+)', url)
    if m:
        return m.group(1)
    # sku=12345 参数
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if 'sku' in params:
        return params['sku'][0]
    return None


# ── 浏览器管理 ────────────────────────────────────────────────
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

    # 反反爬 - 添加真实的浏览器特征
    co.set_argument('--disable-features=IsolateOrigins,site-per-process')

    # 添加真实的User-Agent
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

    return co


def _create_page(co):
    """创建浏览器页面，带异常处理"""
    from DrissionPage import ChromiumPage
    try:
        return ChromiumPage(co)
    except Exception as e:
        logger.error(f'DrissionPage创建页面失败: {e}')
        raise


def _safe_quit_page(page):
    """安全关闭浏览器页面"""
    if page:
        try:
            page.quit()
        except Exception:
            pass


# ── 商品卡片查找 (带5种备用选择器) ────────────────────────────
def _find_product_cards(page, selectors):
    """查找商品卡片，支持多种选择器和完整备用链"""
    # 第1步: 使用当前页面类型的主选择器
    card_selectors = selectors['card'].split(', ')
    for sel in card_selectors:
        try:
            cards = page.eles(sel.strip())
            if cards:
                return cards
        except Exception:
            continue

    # 第2步: 依次尝试所有备用选择器
    for sel in FALLBACK_CARD_SELECTORS:
        try:
            cards = page.eles(sel)
            if cards and len(cards) > 0:
                logger.info(f'使用备用选择器找到商品: {sel}')
                return cards
        except Exception:
            continue

    return []


# ── 商品数据提取 (带备用选择器) ────────────────────────────────
def _get_sku(card, selectors):
    """获取SKU ID"""
    try:
        sku = card.attr(selectors.get('sku_attr', 'data-sku')) or ''
        if sku:
            return sku
        # 尝试从链接中提取
        for link in card.eles('css:a'):
            href = link.attr('href') or ''
            m = re.search(r'/(\d+)\.html', href)
            if m:
                return m.group(1)
            m = re.search(r'sku=(\d+)', href)
            if m:
                return m.group(1)
    except Exception:
        pass
    return str(id(card))


def _extract_title(card, selectors):
    """提取标题，主选择器失败后尝试5种备用选择器"""
    # 主选择器
    title_selectors = selectors['title'].split(', ')
    for sel in title_selectors:
        try:
            title_el = card.ele(sel.strip())
            if title_el:
                title = title_el.attr('title') or title_el.text.strip()
                if title:
                    return title
        except Exception:
            continue

    # 备用选择器
    for sel in FALLBACK_TITLE_SELECTORS:
        try:
            title_el = card.ele(sel)
            if title_el:
                title = title_el.attr('title') or title_el.text.strip()
                if title:
                    return title
        except Exception:
            continue

    # 最终备用: 查找最长的文本
    try:
        best = ''
        for el in card.eles('css:span, css:a, css:div'):
            try:
                text = el.text.strip()
                if len(text) > len(best) and len(text) > 5:
                    best = text
            except Exception:
                continue
        if best:
            return best
    except Exception:
        pass

    return ''


def _extract_price(card, selectors):
    """提取价格，主选择器失败后尝试5种备用选择器"""
    # 主选择器
    price_selectors = selectors['price'].split(', ')
    for sel in price_selectors:
        try:
            for el in card.eles(sel.strip()):
                cls = el.attr('class') or ''
                if '_gray_' in cls or '_subsidy_' in cls:
                    continue
                text = el.text.strip()
                m = re.search(r'(\d+\.?\d*)', text)
                if m:
                    return float(m.group(1))
        except Exception:
            continue

    # 备用选择器
    for sel in FALLBACK_PRICE_SELECTORS:
        try:
            el = card.ele(sel)
            if el:
                cls = el.attr('class') or ''
                if '_gray_' in cls or '_subsidy_' in cls:
                    continue
                text = el.text.strip()
                m = re.search(r'(\d+\.?\d*)', text)
                if m:
                    return float(m.group(1))
        except Exception:
            continue

    return 0


def _extract_product(card, selectors, page_type):
    """从卡片提取数据"""
    data = {}

    # SKU & URL
    sku = _get_sku(card, selectors)
    data['product_url'] = f'https://item.jd.com/{sku}.html' if sku and not sku.startswith('__') else ''

    # 标题 - 使用带备用的提取函数
    data['name'] = _extract_title(card, selectors)
    if not data['name']:
        return None

    # 价格 - 使用带备用的提取函数
    data['price'] = _extract_price(card, selectors)

    # 原价
    data['original_price'] = None
    try:
        gray_el = card.ele('css:[class*="_gray_"], css:.p-price del')
        if gray_el:
            m = re.search(r'(\d+\.?\d*)', gray_el.text)
            if m:
                data['original_price'] = float(m.group(1))
    except Exception:
        pass

    # 图片
    data['image_url'] = ''
    try:
        for img in card.eles('css:img'):
            src = img.attr('src') or img.attr('data-src') or ''
            if src and ('360buyimg' in src or 'jd.com' in src) and 'icon' not in src.lower():
                data['image_url'] = src
                break
        if not data['image_url']:
            first_img = card.ele('css:img[src]')
            if first_img:
                data['image_url'] = first_img.attr('src') or ''
    except Exception:
        pass

    # 店铺/平台
    data['platform'] = '京东'
    try:
        if card.ele('css:img[alt="自营"], css:.p-icons .自营'):
            data['platform'] = '京东自营'
    except Exception:
        pass

    # 销量/评论
    data['comment_count'] = 0
    try:
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
    except Exception:
        pass

    data['rating'] = None
    data['category'] = '京东'
    return data


# ── 静态请求备用方案 ──────────────────────────────────────────
def _try_static_request(url, count, message_callback=None):
    """当动态页面完全失败时，尝试用静态HTTP请求获取基础数据"""
    if message_callback:
        message_callback('动态页面失败，尝试静态请求备用方案...')
    products = []

    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.jd.com/',
        }

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # 尝试从HTML中提取SKU和价格信息
        # 京东搜索页常在<script>标签中嵌入JSON数据
        json_matches = re.findall(r'"sku":\s*"?(\d+)"?', html)
        price_matches = re.findall(r'"p":\s*"?(\d+\.?\d*)"?', html)
        name_matches = re.findall(r'"t":\s*"([^"]+)"', html)

        seen = set()
        for i, sku in enumerate(json_matches):
            if len(products) >= count:
                break
            if sku in seen:
                continue
            seen.add(sku)
            product = {
                'name': name_matches[i] if i < len(name_matches) else '',
                'price': float(price_matches[i]) if i < len(price_matches) else 0,
                'original_price': None,
                'platform': '京东',
                'rating': None,
                'comment_count': 0,
                'category': '京东',
                'user_age': None,
                'user_gender': '',
                'user_region': '',
                'image_url': '',
                'product_url': f'https://item.jd.com/{sku}.html',
                'scraped_at': '',
            }
            if product['name']:
                products.append(product)

        if products and message_callback:
            message_callback(f'静态请求获取到 {len(products)} 条数据')

    except ImportError:
        logger.warning('requests库未安装，无法使用静态请求备用方案')
        if message_callback:
            message_callback('缺少requests库，无法使用静态请求备用方案')
    except Exception as e:
        logger.warning(f'静态请求备用方案失败: {e}')
        if message_callback:
            message_callback('静态请求备用方案失败')

    return products


# ── Selenium 备用方案 ──────────────────────────────────────────
def _try_selenium_fallback(url, count, stop_check=None, progress_callback=None, message_callback=None):
    """当DrissionPage完全失败时，尝试使用Selenium"""
    if message_callback:
        message_callback('DrissionPage失败，尝试Selenium备用方案...')

    products = []
    driver = None

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        opts = Options()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1280,900')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_argument(f'--user-data-dir={PROFILE_DIR}')
        opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.get(url)
        time.sleep(3)

        # 检查是否需要登录
        if 'passport.jd.com' in driver.current_url or 'login' in driver.current_url.lower():
            if message_callback:
                message_callback('Selenium模式: 京东需要登录，请在浏览器窗口中登录...')
            start = time.time()
            while time.time() - start < LOGIN_TIMEOUT:
                if stop_check and stop_check():
                    return []
                if 'passport.jd.com' not in driver.current_url and 'login' not in driver.current_url.lower():
                    break
                time.sleep(1.5)
            else:
                if message_callback:
                    message_callback('Selenium模式: 登录超时')
                return []
            driver.get(url)
            time.sleep(3)

        # 尝试提取商品
        seen_skus = set()
        for sel in FALLBACK_CARD_SELECTORS[:5]:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel.replace('css:', ''))
                if not elements:
                    continue
                for card_el in elements:
                    if len(products) >= count:
                        break
                    if stop_check and stop_check():
                        break
                    try:
                        product = _extract_product_selenium(card_el, driver)
                        sku = product.get('product_url', '').split('/')[-1].replace('.html', '') if product else ''
                        if product and product.get('name') and sku not in seen_skus:
                            seen_skus.add(sku)
                            products.append(product)
                            if progress_callback:
                                progress_callback(len(products), count)
                    except Exception:
                        continue
                if products:
                    break
            except Exception:
                continue

        if products and message_callback:
            message_callback(f'Selenium备用方案获取到 {len(products)} 条数据')

    except ImportError:
        logger.warning('Selenium未安装，无法使用Selenium备用方案')
        if message_callback:
            message_callback('缺少selenium库，无法使用Selenium备用方案')
    except Exception as e:
        logger.warning(f'Selenium备用方案失败: {e}')
        if message_callback:
            message_callback(f'Selenium备用方案失败: {_friendly_error(str(e))}')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return products


def _extract_product_selenium(card_el, driver):
    """从Selenium元素提取商品数据"""
    from selenium.webdriver.common.by import By
    data = {
        'platform': '京东',
        'rating': None,
        'comment_count': 0,
        'category': '京东',
        'original_price': None,
        'user_age': None,
        'user_gender': '',
        'user_region': '',
        'scraped_at': '',
    }

    # SKU
    sku = card_el.get_attribute('data-sku') or ''
    data['product_url'] = f'https://item.jd.com/{sku}.html' if sku else ''

    # 标题
    data['name'] = ''
    for sel in ['span[title]', '.p-name a em', '.sku-name']:
        try:
            title_el = card_el.find_element(By.CSS_SELECTOR, sel)
            if title_el:
                title = title_el.get_attribute('title') or title_el.text.strip()
                if title:
                    data['name'] = title
                    break
        except Exception:
            continue

    if not data['name']:
        return None

    # 价格
    data['price'] = 0
    for sel in ['[class*="_price_"]', '.p-price i', 'span[class*="price"]']:
        try:
            price_el = card_el.find_element(By.CSS_SELECTOR, sel)
            if price_el:
                m = re.search(r'(\d+\.?\d*)', price_el.text)
                if m:
                    data['price'] = float(m.group(1))
                    break
        except Exception:
            continue

    # 图片
    data['image_url'] = ''
    try:
        img = card_el.find_element(By.CSS_SELECTOR, 'img')
        data['image_url'] = img.get_attribute('src') or img.get_attribute('data-src') or ''
    except Exception:
        pass

    return data


# ── 主入口 ────────────────────────────────────────────────────
def scrape_jd(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """京东爬虫主入口

    带完整的异常处理和备用方案:
    1. 网络超时 -> 自动重试3次
    2. 页面加载失败 -> 刷新页面
    3. 选择器失效 -> 5种备用选择器
    4. 反爬虫检测 -> 自动等待并重试
    5. 浏览器崩溃 -> 自动重启
    6. DrissionPage失败 -> Selenium备用
    7. 动态页面失败 -> 静态请求备用
    """
    page = None
    products = []
    seen_skus = set()
    page_num = 1
    browser_crash_retries = 0
    base_url = url or 'https://search.jd.com/Search?keyword=手机'

    while browser_crash_retries <= MAX_BROWSER_CRASH_RETRIES:
        try:
            if message_callback:
                message_callback('正在初始化浏览器...')

            co = _create_options()
            co.headless(False)

            # 使用固定目录保存登录状态
            os.makedirs(PROFILE_DIR, exist_ok=True)
            co.set_argument(f'--user-data-dir={PROFILE_DIR}')

            page = _create_page(co)
            page.set.load_mode.eager()

            # 处理URL - 支持所有京东链接格式
            original_url = url or 'https://search.jd.com/Search?keyword=手机'
            base_url = _clean_jd_url(original_url)  # update outer scope

            # URL转换通知
            if base_url != original_url:
                if 're.jd.com' in original_url:
                    if message_callback:
                        message_callback('检测到短链接，已自动转换为标准搜索页...')
                elif 'm.jd.com' in original_url:
                    if message_callback:
                        message_callback('检测到移动端链接，已自动转换为桌面端...')
                elif 'item.jd.com' in original_url:
                    if message_callback:
                        message_callback('检测到商品详情页，将提取该商品信息...')
                elif 'mall.jd.com' in original_url:
                    if message_callback:
                        message_callback('检测到店铺页面，将采集店铺商品...')

            if message_callback:
                message_callback('正在访问京东...')

            # 加载页面 - 带网络超时重试
            page_url = _build_jd_page_url(base_url, page_num)
            page_loaded = False

            for attempt in range(1, MAX_NETWORK_RETRIES + 1):
                try:
                    page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                    page_loaded = True
                    break
                except Exception as e:
                    logger.warning(f'页面加载第{attempt}次失败: {e}')
                    if message_callback:
                        message_callback(f'页面加载失败 ({attempt}/{MAX_NETWORK_RETRIES})，重试中...')
                    if attempt < MAX_NETWORK_RETRIES:
                        time.sleep(2 * attempt)

            if not page_loaded:
                if message_callback:
                    message_callback('页面加载多次失败，尝试刷新...')
                try:
                    page.refresh()
                    time.sleep(3)
                except Exception:
                    pass

            time.sleep(3)

            # 等待重定向完成
            current_url = page.url or ''
            if 're.jd.com' in original_url and 're.jd.com' not in current_url:
                if message_callback:
                    message_callback('检测到URL跳转，已自动跟随...')
                base_url = _clean_jd_url(current_url)

            # 检测页面类型
            page_type = _detect_page_type(page, current_url)
            if message_callback:
                message_callback(f'检测到页面类型: {page_type}')

            # ── 检测空白页 -> 自动刷新 ──
            if PAGE_REFRESH_ON_BLANK and _is_blank_page(page):
                if message_callback:
                    message_callback('检测到页面空白，自动刷新...')
                try:
                    page.refresh()
                    time.sleep(3)
                except Exception:
                    pass
                # 刷新后重新检测
                page_type = _detect_page_type(page, page.url or '')

            # ── 检测反爬虫 -> 自动等待并重试 ──
            anti_crawl_retries = 0
            while _is_anti_crawl(page) and anti_crawl_retries < MAX_ANTI_CRAWL_RETRIES:
                anti_crawl_retries += 1
                if message_callback:
                    message_callback(f'检测到反爬虫机制，尝试绕过 ({anti_crawl_retries}/{MAX_ANTI_CRAWL_RETRIES})...')

                # 等待更长时间
                wait_time = 5 * anti_crawl_retries
                time.sleep(wait_time)

                try:
                    page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                    time.sleep(3)
                except Exception:
                    pass

                current_url = page.url or ''

                # 如果仍然被拦截，尝试刷新cookies或换UA
                if _is_anti_crawl(page) and anti_crawl_retries >= 2:
                    if message_callback:
                        message_callback('尝试切换浏览器特征...')
                    try:
                        # 执行JavaScript模拟人类行为
                        page.run_js('window.scrollTo(0, document.body.scrollHeight/3)')
                        time.sleep(2)
                        page.run_js('window.scrollTo(0, 0)')
                        time.sleep(2)
                    except Exception:
                        pass

            if _is_anti_crawl(page):
                if message_callback:
                    message_callback('无法绕过反爬虫，建议：手动登录京东账号，或等待10分钟后重试')
                logger.error('京东反爬虫拦截')
                # 不立即返回，尝试切换到静态请求备用方案
                static_products = _try_static_request(base_url, count, message_callback)
                if static_products:
                    return static_products
                return []

            # ── 检测验证码 -> 提示用户 ──
            if _is_captcha_page(page):
                if message_callback:
                    message_callback(f'检测到验证码，请在浏览器窗口中完成验证 ({CAPTCHA_WAIT_SECONDS}秒内)...')
                # 等待用户完成验证码
                captcha_start = time.time()
                while time.time() - captcha_start < CAPTCHA_WAIT_SECONDS:
                    if stop_check and stop_check():
                        return []
                    if not _is_captcha_page(page):
                        if message_callback:
                            message_callback('验证码已通过，继续采集...')
                        break
                    time.sleep(1)
                else:
                    if message_callback:
                        message_callback('验证码等待超时，尝试继续...')
                    # 刷新页面再试
                    try:
                        page.refresh()
                        time.sleep(3)
                    except Exception:
                        pass

            # ── 检测登录过期 -> 提示重新登录 ──
            if _is_login_expired(page):
                if message_callback:
                    message_callback('登录已过期或需要登录，请在浏览器窗口中登录京东账号...')
                if not _wait_for_login(page, stop_check):
                    if message_callback:
                        message_callback('登录超时或取消')
                    return []
                if message_callback:
                    message_callback('登录成功，继续访问...')
                try:
                    page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                    time.sleep(2)
                    page_type = _detect_page_type(page, page.url or '')
                except Exception as e:
                    logger.warning(f'重新加载页面失败: {e}')

            # ── item.jd.com 特殊处理: 单商品详情页 ──
            if page_type == 'item':
                item_products = _scrape_item_page(page, count, stop_check, progress_callback, message_callback)
                _safe_quit_page(page)
                page = None  # prevent double-quit in finally
                return item_products

            if message_callback:
                message_callback('开始采集商品数据...')

            # 获取选择器配置
            selectors = PAGE_SELECTORS.get(page_type, PAGE_SELECTORS['search'])

            # ── 翻页爬取 ──
            consecutive_failures = 0
            while len(products) < count and page_num <= 10:
                if stop_check and stop_check():
                    break

                try:
                    cards = _find_product_cards(page, selectors)

                    if not cards:
                        consecutive_failures += 1

                        if consecutive_failures == 1:
                            # 第1次失败: 尝试滚动页面触发懒加载
                            if message_callback:
                                message_callback('未找到商品，尝试滚动页面...')
                            try:
                                page.scroll.to_bottom()
                                time.sleep(1)
                                page.scroll.to_top()
                                time.sleep(1)
                                cards = _find_product_cards(page, selectors)
                                if cards:
                                    consecutive_failures = 0
                            except Exception:
                                pass

                        if not cards and consecutive_failures == 2:
                            # 第2次失败: 重新检测页面类型
                            if message_callback:
                                message_callback('重新检测页面结构...')
                            new_type = _detect_page_type(page, page.url or '')
                            if new_type != page_type:
                                page_type = new_type
                                selectors = PAGE_SELECTORS.get(page_type, PAGE_SELECTORS['search'])
                                if message_callback:
                                    message_callback(f'已切换到页面类型: {page_type}')
                                consecutive_failures = 0
                                continue

                        if not cards and consecutive_failures == 3:
                            # 第3次失败: 刷新页面
                            if message_callback:
                                message_callback('多次未找到商品，尝试刷新页面...')
                            try:
                                page.refresh()
                                time.sleep(3)
                                cards = _find_product_cards(page, selectors)
                                if cards:
                                    consecutive_failures = 0
                            except Exception:
                                pass

                        if not cards and consecutive_failures >= 4:
                            # 彻底失败
                            if message_callback:
                                message_callback('当前页面未找到商品，尝试下一页...')
                            page_num += 2
                            if page_num <= 10:
                                next_url = _build_jd_page_url(base_url, page_num)
                                for retry in range(MAX_NETWORK_RETRIES):
                                    try:
                                        page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                                        break
                                    except Exception:
                                        if retry < MAX_NETWORK_RETRIES - 1:
                                            time.sleep(2)
                                time.sleep(PAGE_WAIT)
                                # 刷新后重置失败计数
                                consecutive_failures = 0
                            else:
                                break
                            continue

                        if cards:
                            consecutive_failures = 0
                        else:
                            continue

                    consecutive_failures = 0
                    prev_count = len(products)

                    for card in cards:
                        if len(products) >= count:
                            break
                        if stop_check and stop_check():
                            break
                        try:
                            product = _extract_product(card, selectors, page_type)
                            sku = _get_sku(card, selectors)
                            if product and product['name'] and sku not in seen_skus:
                                seen_skus.add(sku)
                                products.append(product)
                                if progress_callback:
                                    progress_callback(len(products), count)
                                if message_callback and len(products) % 5 == 0:
                                    message_callback(f'已采集 {len(products)} 条数据')
                        except Exception as e:
                            logger.debug(f'提取商品失败: {e}')
                            continue

                    if len(products) == prev_count:
                        break

                    # 翻到下一页
                    page_num += 2
                    if len(products) < count:
                        next_url = _build_jd_page_url(base_url, page_num)
                        if message_callback:
                            message_callback(f'正在访问第 {(page_num+1)//2} 页...')
                        for retry in range(MAX_NETWORK_RETRIES):
                            try:
                                page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                                break
                            except Exception as e:
                                logger.warning(f'翻页超时 ({retry+1}/{MAX_NETWORK_RETRIES}): {e}')
                                if retry < MAX_NETWORK_RETRIES - 1:
                                    time.sleep(2 * (retry + 1))

                        time.sleep(PAGE_WAIT)

                except Exception as e:
                    logger.error(f'页面操作出错: {e}')
                    if message_callback:
                        message_callback(f'采集遇到问题，正在保存已获取数据...')
                    break

            if products:
                if message_callback:
                    message_callback(f'采集完成，共获取 {len(products)} 条有效数据')
            else:
                if message_callback:
                    message_callback('未获取到有效数据，尝试备用方案...')

            return products[:count]

        except Exception as e:
            error_str = str(e)
            logger.error(f'京东采集出错: {e}\n{traceback.format_exc()}')

            # 判断是否为浏览器崩溃
            crash_keywords = ['chrome', 'crashed', 'session deleted', 'no such session',
                              'target closed', 'disconnected', 'connection refused',
                              'browser', 'invalid session']
            is_browser_crash = any(kw in error_str.lower() for kw in crash_keywords)

            if is_browser_crash and browser_crash_retries < MAX_BROWSER_CRASH_RETRIES:
                browser_crash_retries += 1
                _safe_quit_page(page)
                page = None
                if message_callback:
                    message_callback(f'浏览器崩溃，自动重启 ({browser_crash_retries}/{MAX_BROWSER_CRASH_RETRIES})...')
                # 清理使用相同 PROFILE_DIR 的残留 Chrome 进程
                try:
                    import subprocess
                    result = subprocess.run(
                        ['wmic', 'process', 'where',
                         f'commandline like \'%{PROFILE_DIR}%\'', 'get', 'processid'],
                        capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.strip().split('\n'):
                        line = line.strip()
                        if line.isdigit():
                            subprocess.run(['taskkill', '/f', '/pid', line],
                                           capture_output=True, timeout=5)
                    time.sleep(3)
                except Exception:
                    pass
                continue  # 重启浏览器重试

            # 非浏览器崩溃或已达到最大重试次数
            if message_callback:
                message_callback(f'采集出错: {_friendly_error(error_str)}')

            # 尝试备用方案
            if not products:
                # 尝试Selenium备用方案
                selenium_products = _try_selenium_fallback(
                    base_url, count, stop_check, progress_callback, message_callback
                )
                if selenium_products:
                    return selenium_products

                # 尝试静态请求备用方案
                static_products = _try_static_request(
                    base_url, count, message_callback
                )
                if static_products:
                    return static_products

            return products

        finally:
            _safe_quit_page(page)


def _scrape_item_page(page, count, stop_check, progress_callback, message_callback):
    """处理 item.jd.com 商品详情页"""
    products = []

    if message_callback:
        message_callback('正在提取商品详情...')

    try:
        data = {
            'platform': '京东',
            'rating': None,
            'comment_count': 0,
            'category': '京东',
            'original_price': None,
            'user_age': None,
            'user_gender': '',
            'user_region': '',
            'scraped_at': '',
        }

        # SKU
        current_url = page.url or ''
        sku = _extract_sku_from_url(current_url) or ''
        data['product_url'] = current_url

        # 标题
        data['name'] = ''
        for sel in ['css:.sku-name', 'css:.itemInfo .name', 'css:.product-intro .name',
                     'css:.p-name', 'css:h1', 'css:.product-name']:
            try:
                el = page.ele(sel)
                if el:
                    text = el.text.strip()
                    if text:
                        data['name'] = text
                        break
            except Exception:
                continue

        if not data['name']:
            if message_callback:
                message_callback('无法提取商品标题')
            return []

        # 价格
        data['price'] = 0
        for sel in ['css:.p-price .price', 'css:[class*="_price_"]', 'css:.price',
                     'css:.p-price i', 'css:span[class*="price"]']:
            try:
                el = page.ele(sel)
                if el:
                    m = re.search(r'(\d+\.?\d*)', el.text or '')
                    if m:
                        data['price'] = float(m.group(1))
                        break
            except Exception:
                continue

        # 原价
        try:
            gray_el = page.ele('css:del, css:[class*="_gray_"], css:.p-price del')
            if gray_el:
                m = re.search(r'(\d+\.?\d*)', gray_el.text or '')
                if m:
                    data['original_price'] = float(m.group(1))
        except Exception:
            pass

        # 图片
        data['image_url'] = ''
        try:
            img = page.ele('css:#spec-img, css:.product-img img, css:.main-img img')
            if img:
                data['image_url'] = img.attr('src') or img.attr('data-src') or ''
        except Exception:
            pass

        # 自营检测
        try:
            if page.ele('css:.icon-self, css:[class*="自营"]'):
                data['platform'] = '京东自营'
        except Exception:
            pass

        products.append(data)
        if message_callback:
            message_callback(f'商品详情提取完成: {data["name"]}')

    except Exception as e:
        logger.warning(f'商品详情页提取失败: {e}')
        if message_callback:
            message_callback(f'商品详情提取失败: {_friendly_error(str(e))}')

    return products


def _friendly_error(error_msg):
    """将技术错误转换为友好提示"""
    error_map = {
        'timeout': '网络连接超时，请检查网络',
        'timed out': '网络连接超时，请检查网络',
        'connection': '无法连接到服务器',
        'connectionrefused': '服务器拒绝连接',
        'connection refused': '服务器拒绝连接',
        'permission': '权限不足',
        'not found': '页面不存在',
        'chrome': '浏览器启动失败',
        'crashed': '浏览器崩溃',
        'session deleted': '浏览器会话丢失',
        'no such session': '浏览器会话丢失',
        'target closed': '浏览器连接断开',
        'disconnected': '浏览器连接断开',
        'dns': 'DNS解析失败，请检查网络',
        'ssl': 'SSL证书错误',
        'proxy': '代理连接失败',
        'socket': '网络连接异常',
    }

    error_lower = error_msg.lower()
    for key, friendly in error_map.items():
        if key in error_lower:
            return friendly

    # 截取前30个字符
    return error_msg[:30] if len(error_msg) > 30 else error_msg


def _wait_for_login(page, stop_check, timeout=LOGIN_TIMEOUT):
    """等待用户登录京东"""
    start = time.time()
    while time.time() - start < timeout:
        if stop_check and stop_check():
            return False
        try:
            current_url = page.url or ''
            if 'passport.jd.com' not in current_url and 'login' not in current_url.lower():
                if 'jd.com' in current_url:
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False
