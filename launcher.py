"""
和金顺数据平台 - 启动器
支持开发环境和打包环境
"""
import os
import sys
import signal
import threading
import webbrowser
import time
import logging
import urllib.request
import urllib.error

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 从 config 导入统一的冻结检测和路径配置
from config import IS_FROZEN, BASE_DIR

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              和 金 顺 数 据 平 台                            ║
║         Hejinshun Data Platform v2.0                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

def print_menu():
    print("""
┌──────────────────────────────────────────────────────────────┐
│  请选择要启动的服务:                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              ║
│   [1] 数据大屏       - 电商数据可视化监控大屏 (port 5001)     │
│                                                              ║
│   [2] 数据工厂       - 结论驱动数据生成器 (port 5007)         │
│                                                              ║
│   [3] 代码生成器     - ECharts代码生成器 (port 5003)          │
│                                                              ║
│   [4] 全部启动       - 同时启动所有服务                       │
│                                                              ║
│   [0] 退出程序                                               │
│                                                              ║
└──────────────────────────────────────────────────────────────┘
""")

# 服务线程列表与停止事件
service_threads = []
service_ports = []  # 记录已启动服务的端口
stop_event = threading.Event()

def _shutdown_flask(port):
    """向Flask开发服务器发送shutdown请求"""
    try:
        req = urllib.request.Request(
            f'http://127.0.0.1:{port}/shutdown',
            method='POST'
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

def shutdown_all_services():
    """停止所有已启动的Flask服务"""
    for port in service_ports:
        logger.info(f"正在停止端口 {port} 上的服务...")
        _shutdown_flask(port)
    stop_event.set()

def run_dashboard_thread(port=5001):
    """在线程中运行数据大屏"""
    try:
        from web import run_dashboard
        run_dashboard(port=port, open_browser=False, stop_event=stop_event)
    except Exception as e:
        if not stop_event.is_set():
            logger.error(f"数据大屏启动失败: {e}")

def run_factory_thread(port=5007):
    """在线程中运行数据工厂"""
    try:
        if IS_FROZEN:
            # 打包环境 - 添加路径到 sys.path
            factory_base = os.path.join(sys._MEIPASS, 'data-factory')
            if factory_base not in sys.path:
                sys.path.insert(0, factory_base)

            import importlib.util
            web_app_path = os.path.join(sys._MEIPASS, 'data-factory', 'web_app.py')
            if os.path.exists(web_app_path):
                spec = importlib.util.spec_from_file_location("web_app", web_app_path)
                web_app = importlib.util.module_from_spec(spec)
                sys.modules['web_app'] = web_app
                spec.loader.exec_module(web_app)
                web_app.run_app(port=port, open_browser=False, stop_event=stop_event)
            else:
                logger.error(f"找不到 web_app.py")
        else:
            import importlib.util
            factory_path = os.path.join(BASE_DIR, 'data-factory', 'web_app.py')
            spec = importlib.util.spec_from_file_location("web_app", factory_path)
            web_app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(web_app)
            web_app.run_app(port=port, open_browser=False, stop_event=stop_event)
    except Exception as e:
        if not stop_event.is_set():
            logger.error(f"数据工厂启动失败: {e}")

def run_generator_thread(port=5003):
    """在线程中运行代码生成器"""
    try:
        from web import run_generator
        run_generator(port=port, open_browser=False, stop_event=stop_event)
    except Exception as e:
        if not stop_event.is_set():
            logger.error(f"代码生成器启动失败: {e}")

def start_single_service(service_func, name, port):
    """启动单个服务（主线程阻塞运行）"""
    service_ports.append(port)
    print(f"\n正在启动{name}...")
    print(f"访问地址: http://127.0.0.1:{port}")
    print("按 Ctrl+C 可停止服务\n")
    try:
        service_func()
    except KeyboardInterrupt:
        print(f"\n正在停止{name}...")
        shutdown_all_services()
        _wait_threads(timeout=5)
        print(f"{name}已停止")

def start_all():
    """启动所有服务"""
    global service_threads

    print("\n正在启动所有服务...\n")

    # 启动数据大屏
    print("  [1/3] 启动数据大屏... http://127.0.0.1:5001")
    t1 = threading.Thread(target=run_dashboard_thread, args=(5001,), daemon=True)
    t1.start()
    service_threads.append(t1)
    service_ports.append(5001)
    time.sleep(1)

    # 启动数据工厂
    print("  [2/3] 启动数据工厂... http://127.0.0.1:5007")
    t2 = threading.Thread(target=run_factory_thread, args=(5007,), daemon=True)
    t2.start()
    service_threads.append(t2)
    service_ports.append(5007)
    time.sleep(1)

    # 启动代码生成器
    print("  [3/3] 启动代码生成器... http://127.0.0.1:5003")
    t3 = threading.Thread(target=run_generator_thread, args=(5003,), daemon=True)
    t3.start()
    service_threads.append(t3)
    service_ports.append(5003)
    time.sleep(2)

    print("\n" + "="*60)
    print("  所有服务已启动!")
    print("="*60)
    print("\n  服务地址:")
    print("    - 数据大屏:     http://127.0.0.1:5001")
    print("    - 数据工厂:     http://127.0.0.1:5007")
    print("    - 代码生成器:   http://127.0.0.1:5003")
    print("\n  按 Ctrl+C 停止所有服务")
    print("="*60 + "\n")

    # 自动打开数据大屏
    time.sleep(1)
    try:
        webbrowser.open('http://127.0.0.1:5001')
    except Exception:
        pass

    # 保持主线程运行，等待停止信号
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
            alive = sum(1 for t in service_threads if t.is_alive())
            if alive == 0:
                print("\n所有服务已停止")
                break
    except KeyboardInterrupt:
        print("\n\n正在停止所有服务...")
        shutdown_all_services()
        _wait_threads(timeout=5)
        print("所有服务已停止")

def _wait_threads(timeout=5):
    """等待服务线程结束，带超时"""
    deadline = time.time() + timeout
    for t in service_threads:
        remaining = max(0, deadline - time.time())
        t.join(timeout=remaining)

def _signal_handler(signum, frame):
    """信号处理函数"""
    print("\n收到停止信号，正在关闭服务...")
    shutdown_all_services()
    _wait_threads(timeout=5)
    print("感谢使用和金顺数据平台!")
    sys.exit(0)

def get_input(prompt, timeout=None):
    """安全的输入函数，处理EOF和超时"""
    try:
        if sys.stdin.isatty():
            return input(prompt).strip()
        else:
            # 非终端模式，使用select
            import select
            if select.select([sys.stdin], [], [], timeout or 5)[0]:
                return sys.stdin.readline().strip()
            return None
    except EOFError:
        return None
    except Exception:
        return None

def main():
    # 注册信号处理
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _signal_handler)

    # 检查命令行参数
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # 如果有参数，直接启动对应服务
    if args:
        if '--all' in args or '-a' in args:
            start_all()
            return
        elif '--dashboard' in args or '-d' in args:
            start_single_service(run_dashboard_thread, "数据大屏", 5001)
            return
        elif '--factory' in args or '-f' in args:
            start_single_service(run_factory_thread, "数据工厂", 5007)
            return
        elif '--generator' in args or '-g' in args:
            start_single_service(run_generator_thread, "代码生成器", 5003)
            return

    # 交互式菜单
    while not stop_event.is_set():
        clear_screen()
        print_banner()
        print_menu()

        try:
            choice = get_input("请输入选项 [0-4]: ")
        except KeyboardInterrupt:
            print("\n\n感谢使用和金顺数据平台!")
            break
        except Exception:
            choice = None

        if choice is None:
            # 无法获取输入，默认启动所有服务
            print("\n自动启动所有服务...")
            start_all()
            break

        if choice == '1':
            start_single_service(run_dashboard_thread, "数据大屏", 5001)
        elif choice == '2':
            start_single_service(run_factory_thread, "数据工厂", 5007)
        elif choice == '3':
            start_single_service(run_generator_thread, "代码生成器", 5003)
        elif choice == '4':
            start_all()
        elif choice == '0':
            print("\n感谢使用和金顺数据平台!")
            stop_event.set()
            time.sleep(0.5)
            break
        else:
            print("\n无效选项，请重新选择")
            time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        shutdown_all_services()
        _wait_threads(timeout=5)
        print("\n\n感谢使用和金顺数据平台!")
    except Exception as e:
        shutdown_all_services()
        print(f"\n程序错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
