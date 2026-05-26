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
        elif order_by == 'created_at':
            products.sort(key=lambda p: p.get('created_at', '') or p.get('scraped_at', ''), reverse=True)
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
                _update_status(message='📡 正在连接数据源...')
                products = scrape(
                    count=count,
                    url=url,
                    stop_check=lambda: _scrape_status['should_stop'],
                    progress_callback=lambda cur, tot: _update_status(
                        current=cur, message=f'🔄 正在采集数据 {cur}/{tot}'),
                    message_callback=lambda msg: _update_status(message=msg)
                )

                if not products:
                    _update_status(running=False, message='❌ 未获取到有效数据')
                    return

                # 阶段2：数据清洗
                _update_status(message='🔧 开始数据清洗处理...')
                cleaned = clean_records(products)

                # 阶段3：数据入库
                if cleaned:
                    _update_status(message='💾 保存原始数据...')
                    save_raw(products)

                    _update_status(message='📊 合并已有数据...')
                    existing = read_cleaned()
                    merged = merge_data(existing, cleaned)

                    _update_status(message='💾 写入存储引擎...')
                    save_cleaned(merged)

                _update_status(running=False, current=len(products),
                               message=f'✅ 完成！共入库 {len(cleaned)} 条数据')
                logger.info('数据采集完成 — %d 条', len(products))
            except Exception as exc:
                logger.exception('数据采集出错')
                _update_status(running=False, message=f'❌ 出错: {exc}')

        t = threading.Thread(target=_task, daemon=True)
        t.start()
        return jsonify({'success': True, 'message': '数据采集任务已启动'})

    @app.route('/api/scrape/search', methods=['POST'])
    def api_scrape_search():
        """关键词搜索采集：根据平台和关键词自动构建搜索URL"""
        with _status_lock:
            if _scrape_status['running']:
                return jsonify({'error': '数据采集任务正在进行中，请等待完成或停止当前任务'}), 400
            _scrape_status['running'] = True
            _scrape_status['total'] = 0
            _scrape_status['current'] = 0
            _scrape_status['message'] = '准备采集...'
            _scrape_status['should_stop'] = False

        data = request.get_json() or {}
        keyword = data.get('keyword', '').strip()
        platform = data.get('platform', 'jd').strip().lower()
        count = max(1, min(int(data.get('count', 50)), 200))

        if not keyword and platform != 'all':
            with _status_lock:
                _scrape_status['running'] = False
            return jsonify({'error': '关键词不能为空'}), 400

        # 根据平台构建搜索URL
        from urllib.parse import quote
        if platform == 'all':
            # 全部平台模式：依次采集各平台
            platforms_to_scrape = ['jd', 'smzdm']
            platform_labels = {'jd': '京东', 'smzdm': '什么值得买'}
            _update_status(total=count, message=f'准备从全部平台采集 {count} 条数据...')

            def _task():
                try:
                    from crawler import scrape_jd, scrape_smzdm
                    from storage import (
                        ensure_dirs, clean_records, merge_data,
                        save_raw, save_cleaned, read_cleaned
                    )

                    all_products = []
                    per_platform_count = max(1, count // len(platforms_to_scrape))

                    for pform in platforms_to_scrape:
                        if _scrape_status['should_stop']:
                            break

                        _update_status(message=f'📡 正在从{platform_labels[pform]}采集...')

                        if pform == 'jd':
                            url = f'https://search.jd.com/Search?keyword={quote(keyword)}' if keyword else None
                            result = scrape_jd(
                                count=per_platform_count,
                                url=url,
                                stop_check=lambda: _scrape_status['should_stop'],
                                progress_callback=lambda cur, tot: _update_status(
                                    current=len(all_products) + cur, message=f'🔄 {platform_labels[pform]}采集 {cur}/{tot}'),
                                message_callback=lambda msg: _update_status(message=msg)
                            )
                        else:
                            url = f'https://search.smzdm.com/?c=home&s={quote(keyword)}' if keyword else None
                            result = scrape_smzdm(
                                count=per_platform_count,
                                url=url,
                                stop_check=lambda: _scrape_status['should_stop'],
                                progress_callback=lambda cur, tot: _update_status(
                                    current=len(all_products) + cur, message=f'🔄 {platform_labels[pform]}采集 {cur}/{tot}'),
                                message_callback=lambda msg: _update_status(message=msg)
                            )

                        if result:
                            all_products.extend(result)

                    if not all_products:
                        _update_status(running=False, message='❌ 未获取到有效数据')
                        return

                    _update_status(message='🔧 开始数据清洗处理...')
                    cleaned = clean_records(all_products)

                    if cleaned:
                        _update_status(message='💾 保存原始数据...')
                        save_raw(all_products)

                        _update_status(message='📊 合并已有数据...')
                        existing = read_cleaned()
                        merged = merge_data(existing, cleaned)

                        _update_status(message='💾 写入存储引擎...')
                        save_cleaned(merged)

                    _update_status(running=False, current=len(all_products),
                                   message=f'✅ 完成！共入库 {len(cleaned)} 条数据')
                    logger.info('全部平台采集完成 — %d 条', len(all_products))
                except Exception as exc:
                    logger.exception('全部平台采集出错')
                    _update_status(running=False, message=f'❌ 出错: {exc}')

            t = threading.Thread(target=_task, daemon=True)
            t.start()
            return jsonify({'success': True, 'message': '全部平台采集任务已启动'})

        elif platform == 'jd':
            url = f'https://search.jd.com/Search?keyword={quote(keyword)}'
        elif platform == 'smzdm':
            url = f'https://search.smzdm.com/?c=home&s={quote(keyword)}'
        else:
            with _status_lock:
                _scrape_status['running'] = False
            return jsonify({'error': f'不支持的平台: {platform}，支持: all, jd, smzdm'}), 400

        _update_status(total=count, message=f'准备搜索「{keyword}」采集 {count} 条数据...')

        def _task():
            try:
                from crawler import scrape
                from storage import (
                    ensure_dirs, clean_records, merge_data,
                    save_raw, save_cleaned, read_cleaned
                )

                _update_status(message=f'📡 正在搜索「{keyword}」...')
                products = scrape(
                    count=count,
                    url=url,
                    stop_check=lambda: _scrape_status['should_stop'],
                    progress_callback=lambda cur, tot: _update_status(
                        current=cur, message=f'🔄 正在采集数据 {cur}/{tot}'),
                    message_callback=lambda msg: _update_status(message=msg)
                )

                if not products:
                    _update_status(running=False, message=f'❌ 搜索「{keyword}」未获取到有效数据')
                    return

                _update_status(message='🔧 开始数据清洗处理...')
                cleaned = clean_records(products)

                if cleaned:
                    _update_status(message='💾 保存原始数据...')
                    save_raw(products)

                    _update_status(message='📊 合并已有数据...')
                    existing = read_cleaned()
                    merged = merge_data(existing, cleaned)

                    _update_status(message='💾 写入存储引擎...')
                    save_cleaned(merged)

                _update_status(running=False, current=len(products),
                               message=f'✅ 完成！共入库 {len(cleaned)} 条数据')
                logger.info('关键词搜索采集完成 — 关键词: %s, %d 条', keyword, len(products))
            except Exception as exc:
                logger.exception('关键词搜索采集出错')
                _update_status(running=False, message=f'❌ 出错: {exc}')

        t = threading.Thread(target=_task, daemon=True)
        t.start()
        return jsonify({'success': True, 'message': f'搜索「{keyword}」采集任务已启动', 'url': url})

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

    @app.route('/shutdown', methods=['POST'])
    def shutdown():
        """关闭Flask服务器"""
        func = request.environ.get('werkzeug.server.shutdown')
        if func is not None:
            func()
        return jsonify({'success': True, 'message': '服务正在关闭'})

    @app.route('/api/debug/paths')
    def api_debug_paths():
        """调试端点: 返回当前使用的路径配置（仅开发环境可用）"""
        from config import BASE_DIR, DATA_DIR, CLEANED_DIR, IS_FROZEN
        import os
        # 生产环境禁用此端点
        if IS_FROZEN:
            return jsonify({'error': '此端点仅在开发环境可用'}), 403
        data_file = os.path.join(CLEANED_DIR, 'products.xlsx')
        return jsonify({
            'is_frozen': IS_FROZEN,
            'base_dir': BASE_DIR,
            'data_dir': DATA_DIR,
            'cleaned_dir': CLEANED_DIR,
            'data_file': data_file,
            'file_exists': os.path.exists(data_file),
        })

    return app


def run_dashboard(port=5001, open_browser=True, stop_event=None):
    """运行仪表盘应用"""
    from storage import ensure_dirs
    import threading

    ensure_dirs()

    app = create_dashboard_app()
    url = f'http://127.0.0.1:{port}'
    logger.info(f'启动数据可视化平台: {url}')

    if open_browser:
        webbrowser.open(url)

    # 如果有stop_event，启动一个监控线程，当事件触发时请求shutdown
    if stop_event is not None:
        def _watch_stop():
            stop_event.wait()
            try:
                import urllib.request
                urllib.request.urlopen(f'http://127.0.0.1:{port}/shutdown', timeout=2)
            except Exception:
                pass
        watcher = threading.Thread(target=_watch_stop, daemon=True)
        watcher.start()

    app.run(debug=False, host='127.0.0.1', port=port, threaded=True)
