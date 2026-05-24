"""快速测试SMZDM爬虫"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\合金顺')

# 设置控制台编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from crawler.smzdm_crawler import scrape_smzdm

def test():
    print(">>> 开始测试...")
    products = scrape_smzdm(
        count=10,
        url=None,
        stop_check=None,
        progress_callback=lambda cur, tot: print(f">>> 进度: {cur}/{tot}"),
        message_callback=lambda msg: print(msg)
    )
    print(f"\n>>> 结果: 获取到 {len(products)} 条商品")
    if products:
        print(">>> 商品列表:")
        for i, p in enumerate(products[:10]):
            name = p.get('name', 'N/A')[:50]
            url = p.get('product_url', 'N/A')[:60]
            print(f"  {i+1}. {name}")
            print(f"     URL: {url}")

if __name__ == '__main__':
    test()
