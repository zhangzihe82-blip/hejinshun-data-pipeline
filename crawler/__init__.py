"""
爬虫模块 - 多平台电商数据采集

支持的子模块:
- jd_crawler: 京东爬虫
- smzdm_crawler: 什么值得买爬虫
"""
from .jd_crawler import scrape_jd
from .smzdm_crawler import scrape_smzdm

__all__ = ['scrape_jd', 'scrape_smzdm', 'scrape']


def scrape(count=50, url=None, stop_check=None, progress_callback=None, message_callback=None):
    """
    统一爬取入口，根据URL自动选择爬虫

    Args:
        count: 爬取数量
        url: 目标URL（京东或什么值得买）
        stop_check: 停止检查函数
        progress_callback: 进度回调 (current, total)
        message_callback: 消息回调 (message)

    Returns:
        list[dict]: 商品数据列表
    """
    from urllib.parse import urlparse

    domain = ''
    if url:
        domain = urlparse(url).netloc.lower().replace('www.', '')

    if 'jd.com' in domain:
        return scrape_jd(count, url, stop_check, progress_callback, message_callback)
    else:
        return scrape_smzdm(count, url, stop_check, progress_callback)
