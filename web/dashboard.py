"""
仪表盘子模块
电商数据可视化平台
"""
import os
import sys
import threading
import logging
import webbrowser

from flask import Flask, render_template, request, jsonify

logger = logging.getLogger(__name__)


def create_dashboard_app():
    """创建仪表盘Flask应用"""
    if getattr(sys, 'frozen', False):
        _template_dir = os.path.join(sys._MEIPASS, 'templates')
        app = Flask(__name__, template_folder=_template_dir)
    else:
        # 模板目录在项目根目录
        _root = os.path.dirname(os.path.dirname(__file__))
        _template_dir = os.path.join(_root, 'templates')
        app = Flask(__name__, template_folder=_template_dir)

    # 数据采集状态
    _scrape_status = {
        'running': False,
        'total': 0,
        'current': 0,
        'message': '就绪',
        'should_stop': False,
    }
    _status_lock = threading.Lock()

    def _update_status(**kwargs):
        with _status_lock:
            for k, v in kwargs.items():
                _scrape_status[k] = v

    def _get_status():
        with _status_lock:
            return dict(_scrape_status)

    def _reset_status():
        """重置状态"""
        with _status_lock:
            _scrape_status['running'] = False
            _scrape_status['total'] = 0
            _scrape_status['current'] = 0
            _scrape_status['message'] = '就绪'
            _scrape_status['should_stop'] = False

    # ─── 页面路由 ─────────────────────────────────────────────

    @app.route('/')
    def index():
        return render_template('index.html')

    # ─── API路由 ──────────────────────────────────────────────

    @app.route('/api/status')
    def api_status():
        return jsonify(_get_status())

    @app.route('/api/products')
    def api_products():
        from storage import read_cleaned
        products = read_cleaned()
        order_by = request.args.get('order_by', 'created_at')
        if order_by == 'price':
            products.sort(key=lambda p: p.get('price', 0) or 0, reverse=True)
        elif order_by == 'name':
            products.sort(key=lambda p: p.get('name', ''))
        return jsonify(products)

    @app.route('/api/stats')
    def api_stats():
        from storage import read_cleaned, get_stats
        products = read_cleaned()
        return jsonify(get_stats(products))

    @app.route('/api/scrape', methods=['POST'])
    def api_scrape():
        with _status_lock:
            if _scrape_status['running']:
                return jsonify({'error': '数据采集任务正在进行中，请等待完成或停止当前任务'}), 400
            # 重置状态
            _scrape_status['running'] = True
            _scrape_status['total'] = 0
            _scrape_status['current'] = 0
            _scrape_status['message'] = '准备采集...'
            _scrape_status['should_stop'] = False

        data = request.get_json() or {}
        count = max(1, min(int(data.get('count', 50)), 200))
        url = data.get('url', '').strip() or None

        _update_status(total=count, message=f'准备采集 {count} 条数据...')

        def _task():
            try:
                from crawler import scrape
                from storage import (
                    ensure_dirs, clean_records, merge_data,
                    save_raw, save_cleaned, read_cleaned
                )

                # 阶段1：数据采集
                _update_status(message='>>> from crawler import scrape')
                products = scrape(
                    count=count,
                    url=url,
                    stop_check=lambda: _scrape_status['should_stop'],
                    progress_callback=lambda cur, tot: _update_status(
                        current=cur, message=f'>>> # 进度: {cur}/{tot}'),
                    message_callback=lambda msg: _update_status(message=msg)
                )

                if not products:
                    _update_status(running=False, message='>>> # 未获取到有效数据')
                    return

                # 阶段2：数据清洗
                _update_status(message='>>> from storage import clean_records, save_cleaned')
                _update_status(message=f'>>> cleaned = clean_records(products)  # {len(products)} 条')
                cleaned = clean_records(products)
                _update_status(message=f'>>> # 清洗完成: {len(cleaned)} 条有效数据')

                # 阶段3：数据入库
                if cleaned:
                    _update_status(message='>>> save_raw(products)')
                    save_raw(products)

                    _update_status(message='>>> existing = read_cleaned()')
                    existing = read_cleaned()

                    _update_status(message='>>> merged = merge_data(existing, cleaned)')
                    merged = merge_data(existing, cleaned)
                    _update_status(message=f'>>> # 合并后共 {len(merged)} 条数据')

                    _update_status(message='>>> save_cleaned(merged)')
                    save_cleaned(merged)

                _update_status(running=False, current=len(products),
                               message=f'>>> print("采集完成! 本次入库 {len(cleaned)} 条")')
                logger.info('数据采集完成 — %d 条', len(products))
            except Exception as exc:
                logger.exception('数据采集出错')
                _update_status(running=False, message=f'>>> raise Exception("{str(exc)[:50]}")')

        t = threading.Thread(target=_task, daemon=True)
        t.start()
        return jsonify({'success': True, 'message': '数据采集任务已启动'})

    @app.route('/api/stop', methods=['POST'])
    def api_stop():
        _update_status(should_stop=True, message='正在停止...')
        return jsonify({'success': True, 'message': '停止信号已发送'})

    @app.route('/api/reset', methods=['POST'])
    def api_reset():
        """重置采集状态"""
        _reset_status()
        return jsonify({'success': True, 'message': '状态已重置'})

    @app.route('/api/clear', methods=['DELETE'])
    def api_clear():
        from storage import clear_products
        clear_products()
        return jsonify({'success': True, 'message': '数据已清空'})

    return app


def run_dashboard(port=5001, open_browser=True):
    """运行仪表盘应用"""
    from storage import ensure_dirs
    ensure_dirs()

    app = create_dashboard_app()
    url = f'http://127.0.0.1:{port}'
    logger.info(f'启动数据可视化平台: {url}')

    if open_browser:
        webbrowser.open(url)

    app.run(debug=False, host='127.0.0.1', port=port, threaded=True)
