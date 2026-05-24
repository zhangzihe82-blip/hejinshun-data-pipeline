"""
前端模块 - Web界面展示

子模块:
- dashboard: 数据仪表盘
- generator: ECharts代码生成器
"""
from .dashboard import create_dashboard_app, run_dashboard
from .generator import create_generator_app, run_generator

__all__ = [
    'create_dashboard_app', 'run_dashboard',
    'create_generator_app', 'run_generator',
]
