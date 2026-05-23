"""
什么值得买爬虫子模块
发现频道商品数据采集
"""
import re
import time
import logging

logger = logging.getLogger(__name__)

# 配置参数
INIT_WAIT = 1.0
SCROLL_WAIT = 0.5


def scrape_smzdm(count=50, url=None, stop_check=None, progress_callback=None):
    """什么值得买爬虫主入口"""
    page = None
    products = []
    seen_urls = set()
    stuck = 0

    try:
        co = _create_options()
        co.headless(True)
        page = _create_page(co)

        target = url or 'https://faxian.smzdm.com/'
        page.get(target)
        page.wait.ele_displayed('css:.feed-row,.feed-block,li[articleid]', timeout=5)
        time.sleep(INIT_WAIT)

        while len(products) < count and stuck < 5:
            if stop_check and stop_check():
                break
            try:
                cards = _find_cards_smzdm(page)
                prev = len(products)
                for card in cards:
                    if len(products) >= count:
                        break
                    if stop_check and stop_check():
                        break
                    try:
                        product = _extract_smzdm(card)
                        if product and product['name'] and product['product_url'] not in seen_urls:
                            seen_urls.add(product['product_url'])
                            products.append(product)
                            if progress_callback:
                                progress_callback(len(products), count)
                    except Exception:
                        continue
                stuck = 0 if len(products) > prev else stuck + 1
                if len(products) < count:
                    page.scroll.to_bottom()
                    time.sleep(SCROLL_WAIT)
            except Exception as e:
                logger.warning(f'页面操作出错: {e}')
                break

        return products[:count]
    except Exception as e:
        logger.error(f'什么值得买采集出错: {e}')
        return products
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def _find_cards_smzdm(page):
    """查找商品卡片"""
    for sel in ['.feed-row', '.feed-block', 'li[articleid]', '.card-list li']:
        cards = page.eles(f'css:{sel}')
        if cards:
            return cards
    return []


def _extract_smzdm(card):
    """从什么值得买卡片提取数据"""
    data = {}
    for link in card.eles('css:a'):
        href = link.attr('href') or ''
        text = link.text.strip()
        if text and len(text) > 3 and 'smzdm.com' in href:
            data['name'] = text
            data['product_url'] = href
            break
    if 'name' not in data:
        return None

    data['price'] = _extract_price(card, [
        '.z-highlight', '.red', '.feed-block-price .num', 'span.red', '.price .num', '.price-num'
    ])
    orig = _extract_price(card, ['.feed-block-original-price', '.z-line-through', 'del', '.worth'])
    data['original_price'] = orig if orig else None

    for sel in ['.mall', '.feed-block-extras span', '.bot-part .mall', 'span.mall', '.merchant']:
        el = card.ele(f'css:{sel}')
        if el and el.text.strip():
            data['platform'] = el.text.strip()
            break
    if 'platform' not in data:
        data['platform'] = '未知'

    rating = None
    for sel in ['.rating', '.star', '.feed-block-rating']:
        el = card.ele(f'css:{sel}')
        if el and el.text:
            m = re.search(r'(\d+\.?\d*)', el.text)
            if m:
                rating = float(m.group(1))
                break
    data['rating'] = rating

    cc = 0
    for sel in ['.comment', '.feed-block-comment', '.comments']:
        el = card.ele(f'css:{sel}')
        if el and el.text:
            m = re.search(r'(\d+)', el.text.replace(',', '').replace('k', '000'))
            if m:
                cc = int(m.group(1))
                break
    data['comment_count'] = cc

    img = card.ele('css:img')
    data['image_url'] = (img.attr('src') or img.attr('data-src') or '') if img else ''
    data['category'] = '好价'
    return data


def _extract_price(card, selectors):
    """提取价格"""
    for sel in selectors:
        el = card.ele(f'css:{sel}')
        if el and el.text:
            m = re.search(r'(\d+\.?\d*)', el.text.replace(',', ''))
            if m:
                return float(m.group(1))
    return 0


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
