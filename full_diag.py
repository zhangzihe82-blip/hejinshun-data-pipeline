"""完整诊断脚本 - SMZDM爬虫"""
import sys
import os

# 设置路径
sys.path.insert(0, r'C:\Users\Administrator\Desktop\合金顺')
os.chdir(r'C:\Users\Administrator\Desktop\合金顺')

# 设置日志
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    print("=" * 60)
    print("SMZDM爬虫诊断")
    print("=" * 60)

    # 导入爬虫
    from crawler.smzdm_crawler import scrape_smzdm

    messages = []
    def save_message(msg):
        messages.append(msg)
        print(f"[MSG] {msg}")

    products = scrape_smzdm(
        count=15,
        url=None,
        stop_check=None,
        progress_callback=lambda cur, tot: print(f"[PROGRESS] {cur}/{tot}"),
        message_callback=save_message
    )

    print("\n" + "=" * 60)
    print(f"结果: 获取到 {len(products)} 条商品")
    print("=" * 60)

    if products:
        for i, p in enumerate(products):
            print(f"\n商品 #{i+1}:")
            print(f"  名称: {p.get('name', 'N/A')[:60]}")
            print(f"  链接: {p.get('product_url', 'N/A')}")
            print(f"  价格: {p.get('price', 0)}")
    else:
        print("\n未获取到商品!")
        print("\n消息日志:")
        for m in messages:
            print(f"  {m}")

    return products

if __name__ == '__main__':
    main()
