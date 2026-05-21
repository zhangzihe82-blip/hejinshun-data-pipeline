"""
E-commerce data visualization platform.
Scrapes product data and saves directly to Excel (no database).
"""
import os
import sys
import threading
import logging
import webbrowser

from flask import Flask, render_template, request, jsonify

from storage import (
    ensure_dirs, clean_records, merge_data,
    save_raw, save_cleaned, read_cleaned, get_stats, clear_products,
)
from scraper import scrape

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    _template_dir = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=_template_dir)
else:
    app = Flask(__name__)

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


# ─── Pages ──────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─── API ────────────────────────────────────────────────────

@app.route('/api/status')
def api_status():
    return jsonify(_get_status())


@app.route('/api/products')
def api_products():
    products = read_cleaned()
    order_by = request.args.get('order_by', 'created_at')
    if order_by == 'price':
        products.sort(key=lambda p: p.get('price', 0) or 0, reverse=True)
    elif order_by == 'name':
        products.sort(key=lambda p: p.get('name', ''))
    return jsonify(products)


@app.route('/api/stats')
def api_stats():
    products = read_cleaned()
    return jsonify(get_stats(products))


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    if _scrape_status['running']:
        return jsonify({'error': '爬取任务正在进行中'}), 400

    data = request.get_json() or {}
    count = max(1, min(int(data.get('count', 50)), 200))
    url = data.get('url', '').strip() or None

    _update_status(running=True, total=count, current=0,
                   message=f'准备爬取 {count} 条数据...', should_stop=False)

    def _task():
        try:
            products = scrape(
                count=count,
                url=url,
                stop_check=lambda: _scrape_status['should_stop'],
                progress_callback=lambda cur, tot: _update_status(
                    current=cur, message=f'正在爬取 {cur}/{tot}'),
                message_callback=lambda msg: _update_status(message=msg)
            )

            # Save to Excel: clean -> merge -> save
            cleaned = clean_records(products)
            if cleaned:
                save_raw(products)
                existing = read_cleaned()
                merged = merge_data(existing, cleaned)
                save_cleaned(merged)

            _update_status(running=False, current=len(products),
                           message=f'完成！共入库 {len(cleaned)} 条数据')
            logger.info('爬取完成 — %d 条', len(products))
        except Exception as exc:
            logger.exception('爬取出错')
            _update_status(running=False, message=f'出错: {exc}')

    t = threading.Thread(target=_task, daemon=True)
    t.start()
    return jsonify({'success': True, 'message': '爬取任务已启动'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    _update_status(should_stop=True, message='正在停止...')
    return jsonify({'success': True, 'message': '停止信号已发送'})


@app.route('/api/clear', methods=['DELETE'])
def api_clear():
    clear_products()
    return jsonify({'success': True, 'message': '数据已清空'})


# ─── Entry ──────────────────────────────────────────────────

if __name__ == '__main__':
    ensure_dirs()
    port = 5001
    url = f'http://127.0.0.1:{port}'
    logger.info(f'启动数据可视化平台: {url}')
    webbrowser.open(url)
    app.run(debug=False, host='127.0.0.1', port=port, threaded=True)
