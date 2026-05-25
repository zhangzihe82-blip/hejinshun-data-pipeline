"""
京东爬虫子模块
支持 React 新版页面，需登录
支持多种京东页面类型，自动适配选择器
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
PAGE_LOAD_TIMEOUT = 30

if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(__file__))
PROFILE_DIR = os.path.join(_BASE, 'data', 'chrome_profile')

# 不同页面类型的选择器配置
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
    're_jd': {
        # re.jd.com 短链接跳转页
        'card': 'css:[data-sku], css:.gl-item, css:.J-goods-list .goods-item',
        'title': 'css:span[title], css:.p-name a em, css:.goods-name',
        'sku_attr': 'data-sku',
        'price': 'css:[class*="_price_"], css:.p-price i, css:.goods-price',
    }
}


def scrape_jd(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """京东爬虫主入口"""
    page = None
    products = []
    seen_skus = set()
    page_num = 1

    try:
        if message_callback:
            message_callback('正在初始化浏览器...')

        co = _create_options()
        co.headless(False)

        # 使用固定目录保存登录状态
        os.makedirs(PROFILE_DIR, exist_ok=True)
        co.set_argument(f'--user-data-dir={PROFILE_DIR}')

        page = _create_page(co)
        page.set.load_mode.eager()  # 快速加载模式

        # 处理URL - 支持re.jd.com短链接
        original_url = url or 'https://search.jd.com/Search?keyword=手机'
        base_url = _clean_jd_url(original_url)

        # 如果URL被转换，通知用户
        if base_url != original_url and 're.jd.com' in original_url:
            if message_callback:
                message_callback('检测到短链接，已自动转换为标准搜索页...')

        if message_callback:
            message_callback('正在访问京东...')

        # 加载首页 - 添加超时
        page_url = _build_jd_page_url(base_url, page_num)
        try:
            page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
        except Exception as e:
            if message_callback:
                message_callback('页面加载超时，尝试继续...')
            logger.warning(f'页面加载超时: {e}')

        time.sleep(3)

        # 等待重定向完成（re.jd.com会跳转）
        current_url = page.url or ''
        if 're.jd.com' in original_url and 're.jd.com' not in current_url:
            if message_callback:
                message_callback(f'检测到URL跳转，已自动跟随...')
            base_url = _clean_jd_url(current_url)

        # 检测页面类型
        page_type = _detect_page_type(page, current_url)
        if message_callback:
            message_callback(f'检测到页面类型: {page_type}')

        # 检查是否被反爬虫拦截
        retry_count = 0
        max_retries = 3

        while ('risk_handler' in current_url or 'cfe.m.jd.com' in current_url) and retry_count < max_retries:
            retry_count += 1
            if message_callback:
                message_callback(f'检测到反爬虫机制，尝试绕过 ({retry_count}/{max_retries})...')

            time.sleep(3)
            try:
                page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                time.sleep(3)
            except:
                pass
            current_url = page.url or ''

        if 'risk_handler' in current_url or 'cfe.m.jd.com' in current_url:
            if message_callback:
                message_callback('无法绕过反爬虫，建议：手动登录京东账号，或等待10分钟后重试')
            logger.error('京东反爬虫拦截')
            return []

        # 检查登录
        current_url = page.url or ''
        if 'passport.jd.com' in current_url or 'login' in current_url.lower():
            if message_callback:
                message_callback('京东需要登录，请在浏览器窗口中登录（120秒内）')
            if not _wait_for_login(page, stop_check):
                if message_callback:
                    message_callback('登录超时或取消')
                return []
            if message_callback:
                message_callback('登录成功，继续访问...')
            try:
                page.get(page_url, timeout=PAGE_LOAD_TIMEOUT)
                time.sleep(2)
                # 重新检测页面类型
                page_type = _detect_page_type(page, page.url or '')
            except Exception as e:
                logger.warning(f'重新加载页面失败: {e}')

        if message_callback:
            message_callback('开始采集商品数据...')

        # 获取选择器配置
        selectors = PAGE_SELECTORS.get(page_type, PAGE_SELECTORS['search'])

        # 翻页爬取
        consecutive_failures = 0
        while len(products) < count and page_num <= 10:
            if stop_check and stop_check():
                break

            try:
                # 尝试多种选择器
                cards = _find_product_cards(page, selectors)

                if not cards:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        if message_callback:
                            message_callback('连续多次未找到商品，尝试自动修复...')
                        # 自动修复：重新检测页面类型
                        new_type = _detect_page_type(page, page.url or '')
                        if new_type != page_type:
                            page_type = new_type
                            selectors = PAGE_SELECTORS.get(page_type, PAGE_SELECTORS['search'])
                            if message_callback:
                                message_callback(f'已切换到页面类型: {page_type}')
                            consecutive_failures = 0
                            continue
                        else:
                            break

                    if message_callback:
                        message_callback(f'当前页面未找到商品，尝试下一页...')
                    page_num += 2
                    if page_num <= 10:
                        next_url = _build_jd_page_url(base_url, page_num)
                        try:
                            page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                        except Exception:
                            pass
                        time.sleep(PAGE_WAIT)
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
                    try:
                        page.get(next_url, timeout=PAGE_LOAD_TIMEOUT)
                    except Exception as e:
                        logger.warning(f'翻页超时: {e}')
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
                message_callback('未获取到有效数据，可能原因：页面结构变化、需要登录、或被反爬虫拦截')

        return products[:count]

    except Exception as e:
        logger.error(f'京东采集出错: {e}')
        if message_callback:
            message_callback(f'采集出错: {_friendly_error(str(e))}')
        return products
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def _detect_page_type(page, url):
    """检测页面类型"""
    url = url or ''

    if 'list.jd.com' in url:
        return 'list'
    elif 're.jd.com' in url:
        return 're_jd'

    # 根据页面元素检测
    try:
        if page.eles('css:[data-sku]'):
            return 'search'
        elif page.eles('css:.gl-item'):
            return 'list'
        elif page.eles('css:.J-goods-list .goods-item'):
            return 're_jd'
    except:
        pass

    return 'search'


def _find_product_cards(page, selectors):
    """查找商品卡片，支持多种选择器"""
    card_selectors = selectors['card'].split(', ')

    for sel in card_selectors:
        try:
            cards = page.eles(sel.strip())
            if cards:
                return cards
        except:
            continue

    # 备用选择器
    fallback_selectors = [
        'css:[data-sku]',
        'css:.gl-item',
        'css:.goods-item',
        'css:.product-item',
        'css:[class*="goods"]',
        'css:[class*="product"]',
    ]

    for sel in fallback_selectors:
        try:
            cards = page.eles(sel)
            if cards and len(cards) > 0:
                return cards
        except:
            continue

    return []


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
    except:
        pass
    return str(id(card))


def _extract_product(card, selectors, page_type):
    """从卡片提取数据"""
    data = {}

    # SKU & URL
    sku = _get_sku(card, selectors)
    data['product_url'] = f'https://item.jd.com/{sku}.html' if sku else ''

    # 标题 - 尝试多种方式
    data['name'] = ''
    title_selectors = selectors['title'].split(', ')
    for sel in title_selectors:
        try:
            title_el = card.ele(sel.strip())
            if title_el:
                title = title_el.attr('title') or title_el.text.strip()
                if title:
                    data['name'] = title
                    break
        except:
            continue

    # 备用标题提取
    if not data['name']:
        try:
            # 查找最长的文本
            for el in card.eles('css:span, css:a, css:div'):
                text = el.text.strip()
                if len(text) > len(data['name']) and len(text) > 5:
                    data['name'] = text
        except:
            pass

    if not data['name']:
        return None

    # 价格 - 尝试多种方式
    data['price'] = 0
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
                    data['price'] = float(m.group(1))
                    break
            if data['price'] > 0:
                break
        except:
            continue

    # 原价
    data['original_price'] = None
    try:
        gray_el = card.ele('css:[class*="_gray_"], css:.p-price del')
        if gray_el:
            m = re.search(r'(\d+\.?\d*)', gray_el.text)
            if m:
                data['original_price'] = float(m.group(1))
    except:
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
    except:
        pass

    # 店铺/平台
    data['platform'] = '京东'
    try:
        if card.ele('css:img[alt="自营"], css:.p-icons .自营'):
            data['platform'] = '京东自营'
    except:
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
    except:
        pass

    data['rating'] = None
    data['category'] = '京东'
    return data


def _friendly_error(error_msg):
    """将技术错误转换为友好提示"""
    error_map = {
        'timeout': '网络连接超时，请检查网络',
        'connection': '无法连接到服务器',
        'permission': '权限不足',
        'not found': '页面不存在',
        'chrome': '浏览器启动失败',
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
            # 检查是否已经离开登录页面
            if 'passport.jd.com' not in current_url and 'login' not in current_url.lower():
                # 并且在京东搜索或列表页面
                if 'search.jd.com' in current_url or 'list.jd.com' in current_url or 'jd.com' in current_url:
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def _clean_jd_url(url):
    """清理京东URL，保留关键参数

    对于 re.jd.com 短链接，自动转换为标准搜索URL
    因为 re.jd.com 使用JavaScript动态加载，自动化访问时商品不渲染
    """
    from urllib.parse import urlparse, parse_qs, urlencode

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    # re.jd.com 转换为 search.jd.com
    if 're.jd.com' in netloc:
        # 提取关键词参数
        params = parse_qs(parsed.query)
        keyword = params.get('keyword', [''])[0]
        if keyword:
            new_url = f'https://search.jd.com/Search?keyword={keyword}'
            logger.info(f'URL转换: {url} -> {new_url}')
            return new_url

    # 标准京东URL处理
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

    # 反反爬 - 添加真实的浏览器特征
    co.set_argument('--disable-web-security')
    co.set_argument('--allow-running-insecure-content')
    co.set_argument('--disable-features=IsolateOrigins,site-per-process')

    # 添加真实的User-Agent
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

    return co


def _create_page(co):
    """创建浏览器页面"""
    from DrissionPage import ChromiumPage
    return ChromiumPage(co)
