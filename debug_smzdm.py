"""
SMZDM爬虫诊断脚本
直接检查页面元素结构
"""
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import PageDisconnectedError

def debug_smzdm():
    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    co.headless(False)
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1280,900')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
    co.set_argument('--disable-web-security')
    co.set_argument('--allow-running-insecure-content')

    page = ChromiumPage(addr_or_opts=co)

    try:
        print(">>> 正在访问什么值得买发现频道...")
        page.get('https://faxian.smzdm.com/', timeout=30)
        print(">>> 等待页面加载...")
        time.sleep(8)  # 增加等待时间

        try:
            print(f">>> 页面标题: {page.title}")
        except:
            print(">>> 无法获取页面标题")

        try:
            print(f">>> 当前URL: {page.url}")
        except:
            print(">>> 无法获取当前URL")

        # 测试各种选择器
        selectors = [
            ('css:.feed-card', 'feed-card'),
            ('css:.feed-card-item', 'feed-card-item'),
            ('css:.z-feed-item', 'z-feed-item'),
            ('css:[data-article-id]', 'data-article-id'),
            ('css:article[data-id]', 'article[data-id]'),
            ('css:.feed-row', 'feed-row'),
            ('css:.feed-block', 'feed-block'),
            ('css:li[articleid]', 'li[articleid]'),
            ('css:.feed-list > li', 'feed-list > li'),
            ('css:.card-list > div', 'card-list > div'),
            ('css:article', 'article'),
            ('css:.feed-list', 'feed-list'),
            ('css:ul li', 'ul li'),
            ('css:.list li', '.list li'),
            ('css:a[href*="/p/"]', 'a[href*="/p/"]'),
            ('css:div[class*="feed"]', 'div[class*="feed"]'),
            ('css:div[class*="card"]', 'div[class*="card"]'),
            ('css:div[class*="item"]', 'div[class*="item"]'),
        ]

        found_any = False
        for sel, name in selectors:
            try:
                eles = page.eles(sel, timeout=2)
                if eles and len(eles) > 0:
                    found_any = True
                    print(f">>> 找到 {len(eles)} 个元素: {name} ({sel})")
                    try:
                        first = eles[0]
                        html_preview = first.html[:150] if first.html else 'N/A'
                        print(f"    HTML预览: {html_preview}...")
                    except:
                        pass
                    print()
            except PageDisconnectedError:
                print(">>> 页面连接已断开，正在重新连接...")
                break
            except Exception as e:
                err_msg = str(e)[:50]
                if 'timeout' not in err_msg.lower():
                    print(f">>> 选择器 {name} 出错: {err_msg}")

        if not found_any:
            print(">>> 未找到任何商品卡片元素，检查页面基本结构...")
            try:
                # 尝试获取页面HTML
                html = page.html
                print(f">>> 页面HTML长度: {len(html)} 字符")

                # 检查是否有验证码或反爬页面
                if '验证' in html or 'captcha' in html.lower() or 'cloudflare' in html.lower():
                    print(">>> 检测到验证页面或反爬保护!")
            except Exception as e:
                print(f">>> 无法获取页面HTML: {e}")

        # 获取所有链接
        print("\n>>> 分析页面链接...")
        try:
            all_links = page.eles('css:a', timeout=5)
            print(f">>> 页面共有 {len(all_links)} 个链接")

            # 查找商品链接
            product_links = []
            for link in all_links[:100]:
                try:
                    href = link.attr('href') or ''
                    text = (link.text or '').strip()
                    if text and len(text) > 5 and ('/p/' in href or 'smzdm.com' in href):
                        if '/user/' not in href and '/help/' not in href:
                            product_links.append({
                                'text': text[:50],
                                'href': href
                            })
                except:
                    continue

            print(f"\n>>> 找到 {len(product_links)} 个可能的商品链接:")
            for i, p in enumerate(product_links[:10]):
                print(f"  {i+1}. {p['text'][:40]} -> {p['href'][:60]}")
        except Exception as e:
            print(f">>> 分析链接出错: {e}")

        # 打印页面结构信息
        print("\n>>> 页面主体结构:")
        try:
            body = page.ele('css:body', timeout=5)
            if body:
                children = body.eles('css:> *', timeout=5)
                for i, child in enumerate(children[:10]):
                    try:
                        tag = child.tag or 'unknown'
                        cls = child.attr('class') or ''
                        print(f"  {i+1}. <{tag}> class='{cls[:50]}'")
                    except:
                        pass
        except Exception as e:
            print(f">>> 获取页面结构出错: {e}")

        print("\n>>> 诊断完成，按Enter关闭浏览器...")
        input()

    except Exception as e:
        print(f">>> 出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            page.quit()
        except:
            pass

if __name__ == '__main__':
    debug_smzdm()
