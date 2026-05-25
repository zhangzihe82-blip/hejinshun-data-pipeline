"""
和金顺数据平台 - 启动器
支持开发环境和打包环境
"""
import os
import sys
import threading
import webbrowser
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 检测是否在打包环境中
def is_frozen():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# 获取基础目录
def get_base_dir():
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

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

# 服务线程列表
service_threads = []
running = True

def run_dashboard_thread(port=5001):
    """在线程中运行数据大屏"""
    try:
        from web import run_dashboard
        run_dashboard(port=port, open_browser=False)
    except Exception as e:
        logger.error(f"数据大屏启动失败: {e}")

def run_factory_thread(port=5007):
    """在线程中运行数据工厂"""
    try:
        if is_frozen():
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
                web_app.run_app(port=port, open_browser=False)
            else:
                logger.error(f"找不到 web_app.py")
        else:
            import importlib.util
            factory_path = os.path.join(BASE_DIR, 'data-factory', 'web_app.py')
            spec = importlib.util.spec_from_file_location("web_app", factory_path)
            web_app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(web_app)
            web_app.run_app(port=port, open_browser=False)
    except Exception as e:
        logger.error(f"数据工厂启动失败: {e}")

def run_generator_thread(port=5003):
    """在线程中运行代码生成器"""
    try:
        from web import run_generator
        run_generator(port=port, open_browser=False)
    except Exception as e:
        logger.error(f"代码生成器启动失败: {e}")

def start_single_service(service_func, name, port):
    """启动单个服务"""
    print(f"\n正在启动{name}...")
    print(f"访问地址: http://127.0.0.1:{port}")
    print("按 Ctrl+C 可停止服务\n")
    service_func()

def start_all():
    """启动所有服务"""
    global service_threads

    print("\n正在启动所有服务...\n")

    # 启动数据大屏
    print("  [1/3] 启动数据大屏... http://127.0.0.1:5001")
    t1 = threading.Thread(target=run_dashboard_thread, args=(5001,), daemon=True)
    t1.start()
    service_threads.append(t1)
    time.sleep(1)

    # 启动数据工厂
    print("  [2/3] 启动数据工厂... http://127.0.0.1:5007")
    t2 = threading.Thread(target=run_factory_thread, args=(5007,), daemon=True)
    t2.start()
    service_threads.append(t2)
    time.sleep(1)

    # 启动代码生成器
    print("  [3/3] 启动代码生成器... http://127.0.0.1:5003")
    t3 = threading.Thread(target=run_generator_thread, args=(5003,), daemon=True)
    t3.start()
    service_threads.append(t3)
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
    except:
        pass

    # 保持主线程运行
    try:
        while running:
            time.sleep(1)
            alive = sum(1 for t in service_threads if t.is_alive())
            if alive == 0:
                print("\n所有服务已停止")
                break
    except KeyboardInterrupt:
        print("\n\n正在停止所有服务...")
        print("服务已停止")

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
    global running

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
    while running:
        clear_screen()
        print_banner()
        print_menu()

        try:
            choice = get_input("请输入选项 [0-4]: ")
        except:
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
            running = False
            time.sleep(1)
            break
        else:
            print("\n无效选项，请重新选择")
            time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n感谢使用和金顺数据平台!")
    except Exception as e:
        print(f"\n程序错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
