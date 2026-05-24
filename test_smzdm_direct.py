"""直接测试SMZDM爬虫"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\合金顺')

from crawler.smzdm_crawler import scrape_smzdm

def test():
    print(">>> 开始测试SMZDM爬虫...")
    products = scrape_smzdm(
        count=10,
        url=None,
        stop_check=None,
        progress_callback=lambda cur, tot: print(f">>> 进度: {cur}/{tot}"),
        message_callback=lambda msg: print(msg)
    )
    print(f"\n>>> 结果: 获取到 {len(products)} 条商品")
    if products:
        for i, p in enumerate(products[:5]):
            print(f"  {i+1}. {p.get('name', 'N/A')[:40]} - ¥{p.get('price', 0)}")
    return products

if __name__ == '__main__':
    test()
