"""
什么值得买爬虫子模块
发现频道商品数据采集
"""
import re
import time
import logging

logger = logging.getLogger(__name__)

# 配置参数
INIT_WAIT = 6.0  # 增加初始等待时间
SCROLL_WAIT = 2.0
PAGE_LOAD_TIMEOUT = 30


def scrape_smzdm(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """什么值得买爬虫主入口"""
    page = None
    products = []
    seen_urls = set()
    stuck = 0

    try:
        if message_callback:
            message_callback('>>> from crawler.smzdm import scrape_smzdm')

        co = _create_options()
        page = _create_page(co)
        page.set.load_mode('eager')  # 使用方法调用形式

        target = url or 'https://faxian.smzdm.com/'
        if message_callback:
            message_callback(f'>>> page.get("{target}")')

        try:
            page.get(target, timeout=PAGE_LOAD_TIMEOUT)
        except Exception as e:
            if message_callback:
                message_callback(f'>>> # 页面加载超时: {str(e)[:30]}')
            logger.warning(f'页面加载超时: {e}')

        if message_callback:
            message_callback('>>> time.sleep(6.0)  # 等待页面渲染')
        time.sleep(INIT_WAIT)

        # 输出页面标题和URL
        try:
            title = page.title or '未知标题'
            if message_callback:
                message_callback(f'>>> # 页面标题: {title}')
        except:
            pass

        try:
            current_url = page.url or ''
            if message_callback:
                message_callback(f'>>> # 当前URL: {current_url}')
        except:
            pass

        # 检查页面是否需要刷新加载
        try:
            test_links = page.eles('css:a', timeout=3)
            if len(test_links) < 20:
                if message_callback:
                    message_callback('>>> # 页面加载不完整，等待刷新...')
                time.sleep(3)
                try:
                    page.refresh()
                    time.sleep(5)
                except:
                    pass
        except:
            pass

        # 修复：更新选择器列表 - 正确的选择器是 li[articleid]
        selectors = [
            'css:li[articleid]',  # 主要选择器，已验证有效
            'css:.feed-card',
            'css:.feed-card-item',
            'css:.z-feed-item',
            'css:[data-article-id]',
            'css:article[data-id]',
            'css:.feed-row',
            'css:.feed-block',
            'css:.feed-list > li',
            'css:.card-list > div',
            'css:article',
        ]

        if message_callback:
            message_callback('>>> # 尝试查找商品卡片...')

        # 尝试各种选择器
        found_selector = None
        for sel in selectors:
            try:
                found = page.eles(sel, timeout=3)
                if found and len(found) > 0:
                    found_selector = sel
                    if message_callback:
                        message_callback(f'>>> cards = page.eles("{sel}")  # {len(found)} 个')
                    break
            except Exception as e:
                err_str = str(e)[:30]
                logger.debug(f'选择器 {sel} 出错: {err_str}')
                continue

        # 直接尝试商品链接作为备选
        if not found_selector:
            try:
                product_links = page.eles('css:a[href*="/p/"]', timeout=3)
                if product_links and len(product_links) > 5:
                    if message_callback:
                        message_callback(f'>>> # 找到 {len(product_links)} 个商品链接，直接提取...')
                    found_selector = 'css:a[href*="/p/"]'
            except:
                pass

        if not found_selector:
            # Fallback: 直接从商品链接提取 - 使用更精确的选择器
            if message_callback:
                message_callback('>>> # 未找到商品卡片，从商品链接提取...')

            try:
                # 使用更精确的选择器获取商品链接
                product_links = page.eles('css:a[href*="/p/"]', timeout=5)
                if message_callback:
                    message_callback(f'>>> # 找到 {len(product_links)} 个商品链接')

                for link in product_links[:count * 2]:
                    if stop_check and stop_check():
                        break
                    try:
                        href = link.attr('href') or ''
                        text = (link.text or '').strip()
                        # 只保留有效文本
                        if text and 5 < len(text) < 150:
                            if href not in seen_urls:
                                seen_urls.add(href)
                                product = {
                                    'name': text[:100],
                                    'product_url': href,
                                    'price': 0,
                                    'original_price': None,
                                    'platform': '什么值得买',
                                    'comment_count': 0,
                                    'rating': None,
                                    'image_url': '',
                                    'category': '好价'
                                }
                                products.append(product)
                                if progress_callback:
                                    progress_callback(len(products), count)
                                if message_callback and len(products) <= 5:
                                    name_short = text[:30] + "..." if len(text) > 30 else text
                                    message_callback(f'>>> products.append({{"name": "{name_short}", ...}})  # #{len(products)}')
                                if len(products) >= count:
                                    break
                    except:
                        continue
            except Exception as e:
                if message_callback:
                    message_callback(f'>>> # 提取链接失败: {str(e)[:40]}')

        else:
            # 使用找到的卡片
            cards = page.eles(found_selector)

            while len(products) < count and stuck < 3:
                if stop_check and stop_check():
                    if message_callback:
                        message_callback('>>> break  # 用户取消')
                    break

                try:
                    prev_count = len(products)

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
                                if message_callback:
                                    name_short = product['name'][:25] + "..." if len(product['name']) > 25 else product['name']
                                    price_str = f"¥{product.get('price', 0)}" if product.get('price') else "未知价格"
                                    message_callback(f'>>> products.append({{"name": "{name_short}", "price": "{price_str}"}})  # #{len(products)}')
                        except Exception as e:
                            continue

                    # 检查是否有新数据
                    if len(products) > prev_count:
                        stuck = 0
                    else:
                        stuck += 1

                    if len(products) < count:
                        # 检测是否到达页面底部
                        try:
                            at_bottom = page.run_js('return window.innerHeight + window.scrollY >= document.body.scrollHeight - 100;')
                            if at_bottom and stuck >= 2:
                                if message_callback:
                                    message_callback('>>> # 已到达页面底部')
                                break
                        except:
                            pass

                        if message_callback:
                            message_callback('>>> page.scroll.to_bottom()')

                        page.scroll.to_bottom()
                        time.sleep(SCROLL_WAIT)

                        # 重新获取卡片
                        cards = page.eles(found_selector)

                except Exception as e:
                    if message_callback:
                        message_callback(f'>>> # 页面操作出错: {str(e)[:30]}')
                    break

        if message_callback:
            message_callback(f'>>> return products  # 共 {len(products)} 条')

        return products[:count]

    except Exception as e:
        logger.error(f'什么值得买采集出错: {e}')
        if message_callback:
            message_callback(f'>>> raise Exception("{str(e)[:50]}")')
        return products
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def _extract_smzdm(card):
    """从什么值得买卡片提取数据 - 针对li[articleid]结构优化"""
    data = {}

    # 首先尝试从链接中提取商品信息（最可靠的方法）
    product_link = None
    try:
        links = card.eles('css:a[href*="/p/"]')
        if links:
            product_link = links[0]
    except:
        pass

    if product_link:
        try:
            href = product_link.attr('href') or ''
            text = (product_link.text or '').strip()
            if text and len(text) > 5:
                data['name'] = text[:100]
                data['product_url'] = href
        except:
            pass

    # 如果上面的方法失败，尝试其他链接
    if 'name' not in data:
        try:
            for link in card.eles('css:a'):
                href = link.attr('href') or ''
                text = (link.text or '').strip()
                # 商品链接通常包含 /p/ 且文本较长
                if text and 5 < len(text) < 200 and ('/p/' in href or 'smzdm.com' in href):
                    if '/user/' not in href and '/help/' not in href:
                        data['name'] = text[:100]
                        data['product_url'] = href
                        break
        except:
            pass

    if 'name' not in data:
        return None

    # 价格提取 - 改进选择器
    price_selectors = [
        'css:.feed-card-price .num',
        'css:.price-current',
        'css:.current-price',
        'css:.feed-price-num',
        'css:.feed-block-price .num',
        'css:.price .num',
        'css:span.red',
        'css:em[class*="price"]',
        'css:span[class*="price"]',
    ]
    data['price'] = _extract_price(card, price_selectors)

    # 原价
    orig = _extract_price(card, ['css:.feed-block-original-price', 'css:.z-line-through', 'css:del', 'css:.worth'])
    data['original_price'] = orig if orig else None

    # 平台/商城
    data['platform'] = '什么值得买'
    platform_selectors = ['css:.feed-card-mall', 'css:.mall-name', 'css:.feed-block-extras span', 'css:span.mall', 'css:.mall', 'css:span[class*="mall"]']
    for sel in platform_selectors:
        try:
            el = card.ele(sel)
            if el:
                text = (el.text or '').strip()
                if text and len(text) < 20:
                    data['platform'] = text
                    break
        except:
            continue

    # 评分
    data['rating'] = None
    for sel in ['css:.rating', 'css:.star', 'css:.feed-block-rating', 'css:span[class*="rating"]']:
        try:
            el = card.ele(sel)
            if el and el.text:
                m = re.search(r'(\d+\.?\d*)', el.text)
                if m:
                    data['rating'] = float(m.group(1))
                    break
        except:
            continue

    # 评论数/点赞数
    data['comment_count'] = 0
    try:
        card_text = card.text or ''
        # 尝试匹配 "X评论" 或 "X点赞" 格式
        m = re.search(r'(\d+)\s*(评论|点赞|收藏)', card_text)
        if m:
            data['comment_count'] = int(m.group(1))
    except:
        pass

    # 图片
    data['image_url'] = ''
    try:
        img = card.ele('css:img[src]')
        if img:
            src = img.attr('src') or img.attr('data-src') or ''
            if src and not src.endswith('.gif'):  # 排除gif图片
                data['image_url'] = src
    except:
        pass

    data['category'] = '好价'
    return data


def _extract_price(card, selectors):
    """提取价格"""
    for sel in selectors:
        try:
            el = card.ele(sel) if sel.startswith('css:') else card.ele(f'css:{sel}')
            if el and el.text:
                text = el.text.replace(',', '').replace('￥', '').replace('¥', '')
                m = re.search(r'(\d+\.?\d*)', text)
                if m:
                    return float(m.group(1))
        except:
            continue
    return 0


def _create_options():
    """创建浏览器选项"""
    from DrissionPage import ChromiumOptions
    import random
    co = ChromiumOptions()

    # 设置 Edge 浏览器路径
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

    # 禁用headless模式
    co.headless(False)

    # 使用随机端口避免冲突
    port = random.randint(9300, 9400)
    co.set_local_port(port)

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

    # User-Agent
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

    # 自动关闭浏览器
    co.set_argument('--auto-close')

    return co


def _create_page(co):
    """创建浏览器页面"""
    from DrissionPage import ChromiumPage
    # 创建新的浏览器实例
    return ChromiumPage(addr_or_opts=co)
