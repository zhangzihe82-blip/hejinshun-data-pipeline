"""简单测试 - 直接使用DrissionPage"""
import time
from DrissionPage import ChromiumPage, ChromiumOptions

def simple_test():
    print(">>> 创建浏览器选项...")
    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    co.headless(False)
    co.set_local_port(9350)
    co.set_argument('--no-sandbox')
    co.set_argument('--window-size=1280,900')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')

    print(">>> 创建浏览器页面...")
    page = ChromiumPage(addr_or_opts=co)

    try:
        print(">>> 访问页面...")
        page.get('https://faxian.smzdm.com/', timeout=30)
        print(f">>> 页面标题: {page.title}")
        print(f">>> 当前URL: {page.url}")
        print(">>> 等待页面加载...")
        time.sleep(8)

        print(">>> 查找商品链接...")
        links = page.eles('css:a[href*="/p/"]', timeout=10)
        print(f">>> 找到 {len(links)} 个商品链接")

        if links:
            for i, link in enumerate(links[:5]):
                text = (link.text or '').strip()[:50]
                href = link.attr('href') or ''
                print(f"  {i+1}. {text} -> {href[:50]}")

        print(">>> 查找商品卡片...")
        cards = page.eles('css:li[articleid]', timeout=10)
        print(f">>> 找到 {len(cards)} 个商品卡片")

        print("\n>>> 测试完成!")

    except Exception as e:
        print(f">>> 出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(">>> 关闭浏览器...")
        try:
            page.quit()
        except:
            pass

if __name__ == '__main__':
    simple_test()
