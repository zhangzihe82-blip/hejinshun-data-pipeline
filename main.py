"""
和金顺数据平台 - 主入口

统一调度三大模块:
- crawler: 爬虫模块 (京东、什么值得买)
- storage: 存储模块 (Excel读写、数据清洗)
- web: 前端模块 (仪表盘、代码生成器)
- data-factory: 数据制造工厂 (生成统计数据)

用法:
    python main.py              # 启动仪表盘 (port 5001)
    python main.py --factory    # 启动数据制造工厂 (port 5002)
    python main.py --generator  # 启动代码生成器 (port 5003)
    python main.py --help       # 显示帮助
"""
import sys
import logging
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='和金顺数据平台 - 电商数据采集与可视化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python main.py                    # 启动数据仪表盘
    python main.py --factory          # 启动数据制造工厂
    python main.py --generator        # 启动代码生成器
    python main.py -p 8080            # 指定端口
        '''
    )
    parser.add_argument(
        '-f', '--factory',
        action='store_true',
        help='启动数据制造工厂'
    )
    parser.add_argument(
        '-g', '--generator',
        action='store_true',
        help='启动代码生成器'
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=None,
        help='指定服务端口 (默认: 仪表盘5001, 工厂5002, 生成器5003)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动打开浏览器'
    )
    return parser.parse_args()


def main():
    """主入口函数"""
    args = parse_args()

    # 确定端口
    if args.port:
        port = args.port
    elif args.factory:
        port = 5002
    elif args.generator:
        port = 5003
    else:
        port = 5001

    open_browser = not args.no_browser

    if args.factory:
        # 启动数据制造工厂
        import importlib.util
        import os
        factory_path = os.path.join(os.path.dirname(__file__), 'data-factory', 'web_app.py')
        spec = importlib.util.spec_from_file_location("web_app", factory_path)
        web_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_app)
        logger.info(f'启动数据制造工厂 on port {port}...')
        web_app.run_app(port=port, open_browser=open_browser)
    elif args.generator:
        # 启动代码生成器
        from web import run_generator
        logger.info(f'启动代码生成器 on port {port}...')
        run_generator(port=port, open_browser=open_browser)
    else:
        # 启动数据仪表盘
        from web import run_dashboard
        logger.info(f'启动数据仪表盘 on port {port}...')
        run_dashboard(port=port, open_browser=open_browser)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('服务已停止')
        sys.exit(0)
    except Exception as e:
        logger.error(f'启动失败: {e}')
        sys.exit(1)
