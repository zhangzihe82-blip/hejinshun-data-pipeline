"""
配置加载模块
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG = {
    'fields': {
        'name': {
            'type': 'string',
            'method': 'template',
            'template': '{brand} {category} {feature} {suffix}',
            'required': True
        },
        'price': {
            'type': 'float',
            'method': 'lognormal',
            'mean': 6.0,
            'sigma': 1.0,
            'min': 1.0,
            'max': 10000.0,
            'required': True
        },
        'original_price': {
            'type': 'float',
            'method': 'derived',
            'source': 'price',
            'multiplier_min': 1.05,
            'multiplier_max': 1.3,
            'null_probability': 0.2
        },
        'platform': {
            'type': 'string',
            'method': 'choice',
            'choices': ['京东', '京东自营', '什么值得买'],
            'weights': [0.4, 0.4, 0.2]
        },
        'rating': {
            'type': 'float',
            'method': 'truncated_normal',
            'mean': 4.2,
            'sigma': 0.6,
            'min': 1.0,
            'max': 5.0
        },
        'comment_count': {
            'type': 'integer',
            'method': 'poisson',
            'lambda': 500,
            'min': 0
        },
        'category': {
            'type': 'string',
            'method': 'choice',
            'choices': ['手机', '电脑', '家电', '服装', '食品', '图书', '美妆', '家居']
        },
        'image_url': {
            'type': 'string',
            'method': 'template',
            'template': 'https://img14.360buyimg.com/n1/{id}.jpg'
        },
        'product_url': {
            'type': 'string',
            'method': 'template',
            'template': 'https://item.jd.com/{id}.html',
            'unique': True
        },
        'scraped_at': {
            'type': 'datetime',
            'method': 'uniform_range',
            'start': '2024-01-01',
            'end': '2024-12-31'
        }
    },
    'constraints': [
        {'rule': 'original_price >= price', 'description': '原价应大于等于现价'},
        {'rule': '1.0 <= rating <= 5.0', 'description': '评分应在1-5之间'},
        {'rule': 'comment_count >= 0', 'description': '评论数应非负'}
    ],
    'correlations': [
        {'fields': ['rating', 'comment_count'], 'coefficient': 0.3, 'description': '评分与评论数正相关'}
    ],
    'output': {
        'excel_headers': {
            'name': 'Product Name',
            'price': 'Price',
            'original_price': 'Original Price',
            'platform': 'Platform',
            'rating': 'Rating',
            'comment_count': 'Comment Count',
            'image_url': 'Image URL',
            'product_url': 'Product URL',
            'category': 'Category',
            'scraped_at': 'Scraped At'
        }
    }
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件

    Args:
        config_path: 配置文件路径，如果为None则使用默认配置

    Returns:
        配置字典
    """
    if config_path is None:
        return DEFAULT_CONFIG.copy()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 合并默认配置
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    return merged


def get_field_config(config: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    """获取字段配置"""
    return config.get('fields', {}).get(field_name, {})
