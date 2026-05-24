"""
和金顺数据平台 - 主入口

统一调度三大模块:
- crawler: 爬虫模块
- storage: 存储模块
- web: 前端模块

用法:
    python main.py              # 启动仪表盘
    python main.py --generator  # 启动代码生成器
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    """主入口函数"""
    # 解析命令行参数
    args = sys.argv[1:]

    if '--generator' in args or '-g' in args:
        # 启动代码生成器
        from web import run_generator
        logger.info('启动代码生成器...')
        run_generator(port=5002)
    else:
        # 默认启动仪表盘
        from web import run_dashboard
        logger.info('启动数据仪表盘...')
        run_dashboard(port=5001)


if __name__ == '__main__':
    main()
