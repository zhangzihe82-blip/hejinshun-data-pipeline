"""
结论驱动数据生成引擎

根据用户输入的结论语句或参数，反向推导数据生成规则，
生成支持该结论的统计数据。

支持两种模式:
1. 自然语言结论: "手机品类价格呈上涨趋势"
2. 结构化结论: 年龄范围、性别比例、价格区间等

示例结论:
- "手机品类价格呈上涨趋势"
- "京东自营评分明显高于普通京东"
- "美妆品类评论数最高"
- "高价位商品评分更稳定"
- 结构化: 年龄18-35岁，女性占比65%，价格区间100-500元
"""
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    UP = "上涨"
    DOWN = "下降"
    STABLE = "稳定"
    HIGH = "高"
    LOW = "低"


@dataclass
class UserDemographic:
    """用户人群画像"""
    age_min: int = 18
    age_max: int = 60
    male_ratio: float = 0.5      # 男性占比
    female_ratio: float = 0.5    # 女性占比
    regions: List[str] = field(default_factory=lambda: ['北京', '上海', '广州', '深圳', '杭州'])


@dataclass
class Conclusion:
    """解析后的结论结构"""
    category: str = None          # 品类
    platform: str = None          # 平台
    metric: str = None            # 指标 (price, rating, comment_count)
    direction: TrendDirection = None  # 趋势方向
    comparison: str = None        # 比较对象
    confidence: float = 0.0       # 置信度
    raw_text: str = ""            # 原始文本
    # 新增: 用户画像参数
    demographic: UserDemographic = field(default_factory=UserDemographic)
    price_min: float = None
    price_max: float = None
    regions: List[str] = field(default_factory=list)  # 指定地区列表


class ConclusionParser:
    """结论语句解析器"""

    # 关键词映射
    CATEGORIES = {
        '漆器': ['漆器', '漆艺', '大漆', '雕漆', '脱胎漆器', '推光漆器'],
        '手机': ['手机', '电话', '移动设备'],
        '电脑': ['电脑', '笔记本', '台式机', 'PC'],
        '家电': ['家电', '冰箱', '洗衣机', '空调', '电视'],
        '服装': ['服装', '衣服', '裤子', '鞋', '运动服'],
        '食品': ['食品', '零食', '饮料', '美食'],
        '图书': ['图书', '书籍', '书'],
        '美妆': ['美妆', '化妆品', '护肤'],
        '家居': ['家居', '家具', '家装'],
        '数码': ['数码', '相机', '耳机', '平板'],
    }

    PLATFORMS = {
        '京东自营': ['京东自营', '自营'],
        '京东': ['京东', 'JD'],
        '什么值得买': ['什么值得买', '值得买', 'SMZDM'],
    }

    # 地区关键词映射
    REGION_KEYWORDS = {
        '江浙沪': ['上海', '南京', '苏州', '杭州', '宁波', '无锡', '常州', '南通', '温州', '嘉兴', '绍兴', '金华', '台州', '湖州', '镇江', '扬州', '泰州', '盐城', '徐州'],
        '珠三角': ['广州', '深圳', '东莞', '佛山', '珠海', '中山', '惠州', '江门', '肇庆'],
        '京津冀': ['北京', '天津', '石家庄', '唐山', '保定', '廊坊', '秦皇岛', '邯郸'],
        '长三角': ['上海', '南京', '苏州', '杭州', '宁波', '无锡', '合肥'],
        '成渝': ['成都', '重庆'],
        '北京': ['北京'],
        '上海': ['上海'],
        '广州': ['广州'],
        '深圳': ['深圳'],
        '杭州': ['杭州'],
        '南京': ['南京'],
        '苏州': ['苏州'],
        '成都': ['成都'],
        '武汉': ['武汉'],
        '重庆': ['重庆'],
    }

    METRICS = {
        'price': ['价格', '价位', '售价', '定价'],
        'rating': ['评分', '评价', '星级', '好评'],
        'comment_count': ['评论', '评论数', '评价数', '销量'],
    }

    DIRECTIONS = {
        TrendDirection.UP: ['上涨', '上升', '增长', '提高', '增加', '越来越高'],
        TrendDirection.DOWN: ['下降', '下跌', '降低', '减少', '越来越低'],
        TrendDirection.STABLE: ['稳定', '平稳', '持平', '不变'],
        TrendDirection.HIGH: ['高', '较高', '最高', '领先', '优于'],
        TrendDirection.LOW: ['低', '较低', '最低', '落后'],
    }

    def parse(self, text: str) -> Conclusion:
        """解析结论语句"""
        conclusion = Conclusion(raw_text=text)

        # 提取品类
        for cat, keywords in self.CATEGORIES.items():
            for kw in keywords:
                if kw in text:
                    conclusion.category = cat
                    break
            if conclusion.category:
                break

        # 提取平台
        for platform, keywords in self.PLATFORMS.items():
            for kw in keywords:
                if kw in text:
                    conclusion.platform = platform
                    break
            if conclusion.platform:
                break

        # 提取指标
        for metric, keywords in self.METRICS.items():
            for kw in keywords:
                if kw in text:
                    conclusion.metric = metric
                    break
            if conclusion.metric:
                break

        # 提取方向
        for direction, keywords in self.DIRECTIONS.items():
            for kw in keywords:
                if kw in text:
                    conclusion.direction = direction
                    break
            if conclusion.direction:
                break

        # 提取比较对象
        if '高于' in text or '领先' in text or '优于' in text:
            conclusion.comparison = 'higher_than'
        elif '低于' in text or '落后' in text:
            conclusion.comparison = 'lower_than'
        elif '最' in text:
            if '最高' in text or '最多' in text or '最大' in text:
                conclusion.comparison = 'highest'
            elif '最低' in text or '最少' in text or '最小' in text:
                conclusion.comparison = 'lowest'
            else:
                conclusion.comparison = 'highest'

        # 提取价格区间
        price_pattern = r'价格[区间]?[:：]?\s*(\d+)[~-](\d+)'
        price_match = re.search(price_pattern, text)
        if price_match:
            conclusion.price_min = float(price_match.group(1))
            conclusion.price_max = float(price_match.group(2))

        # 提取年龄范围 (支持"年龄在/为/是25-30岁"等多种表达)
        age_pattern = r'年龄(?:在|为|是|约|大约|[:：])?\s*(\d+)[~-](\d+)岁?'
        age_match = re.search(age_pattern, text)
        if age_match:
            conclusion.demographic.age_min = int(age_match.group(1))
            conclusion.demographic.age_max = int(age_match.group(2))

        # 提取性别比例
        female_pattern = r'女性(?:占比)?[:：]?\s*(\d+)%?'
        female_match = re.search(female_pattern, text)
        if female_match:
            ratio = float(female_match.group(1)) / 100
            conclusion.demographic.female_ratio = ratio
            conclusion.demographic.male_ratio = 1 - ratio

        male_pattern = r'男性(?:占比)?[:：]?\s*(\d+)%?'
        male_match = re.search(male_pattern, text)
        if male_match:
            ratio = float(male_match.group(1)) / 100
            conclusion.demographic.male_ratio = ratio
            conclusion.demographic.female_ratio = 1 - ratio

        # 提取地区信息
        for region_key, cities in self.REGION_KEYWORDS.items():
            if region_key in text:
                conclusion.regions.extend(cities)
        # 去重
        conclusion.regions = list(set(conclusion.regions)) if conclusion.regions else []

        # 计算置信度
        confidence = 0.0
        if conclusion.category: confidence += 0.2
        if conclusion.metric: confidence += 0.2
        if conclusion.direction: confidence += 0.2
        if conclusion.platform or conclusion.comparison: confidence += 0.2
        if conclusion.price_min is not None: confidence += 0.1
        if conclusion.demographic.age_min != 18 or conclusion.demographic.age_max != 60: confidence += 0.1
        if conclusion.regions: confidence += 0.1
        conclusion.confidence = min(1.0, confidence)

        return conclusion

    def parse_structured(self, params: Dict[str, Any]) -> Conclusion:
        """解析结构化参数"""
        conclusion = Conclusion()

        # 品类
        if params.get('category'):
            conclusion.category = params['category']

        # 价格区间
        if params.get('priceMin') is not None:
            conclusion.price_min = float(params['priceMin'])
        if params.get('priceMax') is not None:
            conclusion.price_max = float(params['priceMax'])

        # 年龄范围
        if params.get('ageMin') is not None:
            conclusion.demographic.age_min = int(params['ageMin'])
        if params.get('ageMax') is not None:
            conclusion.demographic.age_max = int(params['ageMax'])

        # 性别比例
        if params.get('femaleRatio') is not None:
            ratio = float(params['femaleRatio']) / 100
            conclusion.demographic.female_ratio = ratio
            conclusion.demographic.male_ratio = 1 - ratio
        elif params.get('maleRatio') is not None:
            ratio = float(params['maleRatio']) / 100
            conclusion.demographic.male_ratio = ratio
            conclusion.demographic.female_ratio = 1 - ratio

        # 平台
        if params.get('platform'):
            conclusion.platform = params['platform']

        # 地区
        if params.get('regions'):
            if isinstance(params['regions'], list):
                conclusion.regions = params['regions']
            elif isinstance(params['regions'], str):
                conclusion.regions = [r.strip() for r in params['regions'].split(',') if r.strip()]

        # 指标和方向
        if params.get('metric'):
            conclusion.metric = params['metric']
        if params.get('direction'):
            for d in TrendDirection:
                if d.value == params['direction']:
                    conclusion.direction = d
                    break

        # 计算置信度
        confidence = 0.0
        if conclusion.category: confidence += 0.2
        if conclusion.price_min is not None: confidence += 0.15
        if conclusion.price_max is not None: confidence += 0.15
        if conclusion.demographic.age_min != 18 or conclusion.demographic.age_max != 60: confidence += 0.15
        if params.get('femaleRatio') is not None or params.get('maleRatio') is not None: confidence += 0.15
        if conclusion.platform: confidence += 0.1
        if conclusion.metric: confidence += 0.1
        conclusion.confidence = min(1.0, confidence)

        return conclusion


class DataRuleGenerator:
    """根据结论生成数据规则"""

    def generate_rules(self, conclusion: Conclusion) -> Dict[str, Any]:
        """根据结论生成数据生成规则"""
        rules = {
            'fields': {},
            'filters': [],
            'adjustments': []
        }

        if conclusion.metric == 'price':
            rules = self._generate_price_rules(conclusion)
        elif conclusion.metric == 'rating':
            rules = self._generate_rating_rules(conclusion)
        elif conclusion.metric == 'comment_count':
            rules = self._generate_comment_rules(conclusion)

        return rules

    def _generate_price_rules(self, conclusion: Conclusion) -> Dict[str, Any]:
        """生成价格相关规则"""
        rules = {'fields': {}, 'filters': [], 'adjustments': []}

        if conclusion.direction == TrendDirection.UP:
            # 价格上涨 → 生成较高价格
            rules['fields']['price'] = {
                'mean': 7.5,  # 对数正态均值，产生更高价格
                'min': 500,
                'max': 10000
            }
            rules['adjustments'].append({
                'type': 'time_trend',
                'metric': 'price',
                'direction': 'up',
                'strength': 0.1
            })

        elif conclusion.direction == TrendDirection.DOWN:
            # 价格下降 → 生成较低价格
            rules['fields']['price'] = {
                'mean': 4.5,
                'min': 10,
                'max': 1000
            }

        elif conclusion.direction == TrendDirection.HIGH:
            # 高价位
            rules['fields']['price'] = {
                'mean': 8.0,
                'min': 1000,
                'max': 50000
            }

        elif conclusion.direction == TrendDirection.LOW:
            # 低价位
            rules['fields']['price'] = {
                'mean': 4.0,
                'min': 1,
                'max': 100
            }

        # 如果指定了品类，调整价格范围
        if conclusion.category:
            category_price_map = {
                '漆器': {'mean': 6.0, 'min': 50, 'max': 50000},  # 漆器价格范围较广
                '手机': {'mean': 7.5, 'min': 500, 'max': 15000},
                '电脑': {'mean': 8.0, 'min': 1000, 'max': 30000},
                '家电': {'mean': 6.5, 'min': 100, 'max': 10000},
                '服装': {'mean': 4.5, 'min': 20, 'max': 2000},
                '食品': {'mean': 3.0, 'min': 1, 'max': 500},
                '图书': {'mean': 3.5, 'min': 5, 'max': 200},
                '美妆': {'mean': 5.5, 'min': 20, 'max': 3000},
                '家居': {'mean': 6.0, 'min': 50, 'max': 20000},
                '数码': {'mean': 7.0, 'min': 100, 'max': 20000},
            }
            if conclusion.category in category_price_map:
                rules['fields']['price'] = category_price_map[conclusion.category]

        return rules

    def _generate_rating_rules(self, conclusion: Conclusion) -> Dict[str, Any]:
        """生成评分相关规则"""
        rules = {'fields': {}, 'filters': [], 'adjustments': []}

        if conclusion.direction == TrendDirection.HIGH:
            rules['fields']['rating'] = {
                'mean': 4.7,
                'sigma': 0.3,
                'min': 4.0,
                'max': 5.0
            }
        elif conclusion.direction == TrendDirection.LOW:
            rules['fields']['rating'] = {
                'mean': 3.5,
                'sigma': 0.8,
                'min': 1.0,
                'max': 4.5
            }

        # 平台比较
        if conclusion.platform == '京东自营' and conclusion.comparison == 'higher_than':
            rules['adjustments'].append({
                'type': 'platform_modifier',
                'platform': '京东自营',
                'metric': 'rating',
                'modifier': 0.3  # 自营评分+0.3
            })

        return rules

    def _generate_comment_rules(self, conclusion: Conclusion) -> Dict[str, Any]:
        """生成评论数相关规则"""
        rules = {'fields': {}, 'filters': [], 'adjustments': []}

        if conclusion.direction == TrendDirection.HIGH:
            rules['fields']['comment_count'] = {
                'lambda': 2000,  # 泊松分布参数
                'min': 500,
                'max': 50000
            }
        elif conclusion.direction == TrendDirection.LOW:
            rules['fields']['comment_count'] = {
                'lambda': 200,
                'min': 0,
                'max': 1000
            }

        # 品类差异
        if conclusion.category:
            category_comment_map = {
                '手机': {'lambda': 3000, 'min': 500},
                '电脑': {'lambda': 2000, 'min': 200},
                '美妆': {'lambda': 5000, 'min': 1000},
                '食品': {'lambda': 1500, 'min': 100},
            }
            if conclusion.category in category_comment_map:
                rules['fields']['comment_count'] = category_comment_map[conclusion.category]

        return rules


class ConclusionDrivenGenerator:
    """结论驱动数据生成器"""

    def __init__(self):
        self.parser = ConclusionParser()
        self.rule_generator = DataRuleGenerator()

    def build_config(self, rules: Dict, conclusion: Conclusion, count: int = 1000, seed: int = None) -> Dict[str, Any]:
        """构建完整的数据生成配置 (公共接口)

        Args:
            rules: 数据生成规则
            conclusion: 解析后的结论
            count: 数据量
            seed: 随机种子

        Returns:
            完整的数据生成配置字典
        """
        return self._build_full_config(rules, conclusion, count, seed)

    def process(self, conclusion_text: str, count: int = 1000, seed: int = None) -> Tuple[Dict[str, Any], Conclusion]:
        """处理结论并生成数据规则

        Args:
            conclusion_text: 结论语句
            count: 生成数据量
            seed: 随机种子

        Returns:
            (数据生成配置, 解析后的结论)
        """
        # 1. 解析结论
        conclusion = self.parser.parse(conclusion_text)
        logger.info(f"解析结论: {conclusion}")

        # 2. 生成规则
        rules = self.rule_generator.generate_rules(conclusion)
        logger.info(f"生成规则: {rules}")

        # 3. 构建完整配置
        config = self._build_full_config(rules, conclusion, count, seed)

        return config, conclusion

    def _build_full_config(self, rules: Dict, conclusion: Conclusion,
                           count: int, seed: int) -> Dict[str, Any]:
        """构建完整的数据生成配置"""

        # 基础字段配置
        base_fields = {
            'name': {
                'type': 'string',
                'method': 'template',
                'template': '{brand} {category} {feature} {suffix}'
            },
            'price': {
                'type': 'float',
                'method': 'lognormal',
                'mean': 6.0,
                'sigma': 1.0,
                'min': 1.0,
                'max': 50000.0
            },
            'original_price': {
                'type': 'float',
                'method': 'derived',
                'null_probability': 0.15
            },
            'platform': {
                'type': 'string',
                'method': 'choice',
                'choices': ['京东', '京东自营', '什么值得买'],
                'weights': [0.35, 0.45, 0.20]
            },
            'rating': {
                'type': 'float',
                'method': 'truncated_normal',
                'mean': 4.2,
                'sigma': 0.5,
                'min': 1.0,
                'max': 5.0
            },
            'comment_count': {
                'type': 'integer',
                'method': 'poisson',
                'lambda': 800,
                'min': 0
            },
            'category': {
                'type': 'string',
                'method': 'choice',
                'choices': ['漆器', '手机', '电脑', '家电', '服装', '食品', '图书', '美妆', '家居']
            },
            # 新增: 用户画像字段
            'user_age': {
                'type': 'integer',
                'method': 'truncated_normal',
                'mean': 35,
                'sigma': 12,
                'min': 18,
                'max': 70
            },
            'user_gender': {
                'type': 'string',
                'method': 'choice',
                'choices': ['男', '女'],
                'weights': [0.5, 0.5]
            },
            'user_region': {
                'type': 'string',
                'method': 'choice',
                'choices': ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '苏州', '重庆', '宁波', '无锡', '厦门', '青岛', '大连', '西安', '长沙', '福州', '合肥', '郑州', '昆明', '南宁', '沈阳', '哈尔滨']
            },
            'image_url': {
                'type': 'string',
                'method': 'template',
                'template': 'https://img14.360buyimg.com/n1/{id}.jpg'
            },
            'product_url': {
                'type': 'string',
                'method': 'template',
                'template': 'https://item.jd.com/{id}.html'
            },
            'scraped_at': {
                'type': 'datetime',
                'method': 'uniform_range',
                'start': '2024-01-01',
                'end': '2024-12-31'
            },
            'created_at': {
                'type': 'datetime',
                'method': 'same_as',
                'source': 'scraped_at'
            }
        }

        # 应用结论规则覆盖基础配置
        for field_name, field_rules in rules.get('fields', {}).items():
            if field_name in base_fields:
                base_fields[field_name].update(field_rules)

        # 如果结论指定了价格区间
        if conclusion.price_min is not None or conclusion.price_max is not None:
            pmin = conclusion.price_min or 1
            pmax = conclusion.price_max or 50000
            base_fields['price']['min'] = pmin
            base_fields['price']['max'] = pmax
            # 根据价格区间调整 lognormal mean 和 sigma
            import math
            price_mid = (pmin + pmax) / 2
            base_fields['price']['mean'] = math.log(price_mid) if price_mid > 0 else 5.5
            # 缩小 sigma 使大部分值落在区间内: sigma ≈ (log(pmax)-log(pmin))/4
            if pmax > pmin and pmin > 0:
                base_fields['price']['sigma'] = max(0.15, (math.log(pmax) - math.log(pmin)) / 4)
            else:
                base_fields['price']['sigma'] = 0.5

        # 如果结论指定了年龄范围
        demo = conclusion.demographic
        if demo.age_min != 18 or demo.age_max != 60:
            base_fields['user_age']['min'] = demo.age_min
            base_fields['user_age']['max'] = demo.age_max
            base_fields['user_age']['mean'] = (demo.age_min + demo.age_max) / 2
            base_fields['user_age']['sigma'] = (demo.age_max - demo.age_min) / 4

        # 如果结论指定了性别比例
        if demo.male_ratio != 0.5 or demo.female_ratio != 0.5:
            # 确保权重总和为1
            total = demo.male_ratio + demo.female_ratio
            male_weight = demo.male_ratio / total
            female_weight = demo.female_ratio / total
            base_fields['user_gender']['weights'] = [male_weight, female_weight]

        # 如果结论指定了地区，调整地区分布
        if conclusion.regions:
            # 指定地区权重占80%，其余均匀分配
            all_regions = base_fields['user_region']['choices']
            region_weights = {}
            for r in conclusion.regions:
                if r in all_regions:
                    region_weights[r] = 0.8 / len(conclusion.regions)
            # 剩余权重均匀分配给其他地区
            remaining_weight = 0.2 / (len(all_regions) - len(region_weights)) if len(all_regions) > len(region_weights) else 0
            weights = []
            for r in all_regions:
                if r in region_weights:
                    weights.append(region_weights[r])
                else:
                    weights.append(max(0.005, remaining_weight))
            total = sum(weights)
            weights = [w / total for w in weights]
            base_fields['user_region']['weights'] = weights

        # 如果结论指定了品类，调整品类分布
        if conclusion.category:
            categories = ['漆器', '手机', '电脑', '家电', '服装', '食品', '图书', '美妆', '家居']
            if conclusion.category in categories:
                # 指定品类占60%，其余均匀分配40%
                weights = [0.05] * len(categories)
                idx = categories.index(conclusion.category)
                weights[idx] = 0.65
                # 确保总和为1
                total = sum(weights)
                weights = [w / total for w in weights]
                base_fields['category']['choices'] = categories
                base_fields['category']['weights'] = weights

        # 如果结论指定了平台，调整平台分布
        if conclusion.platform:
            platforms = ['京东', '京东自营', '什么值得买']
            if conclusion.platform in platforms:
                weights = [0.15, 0.15, 0.15]
                idx = platforms.index(conclusion.platform)
                weights[idx] = 0.7
                # 确保总和为1
                total = sum(weights)
                weights = [w / total for w in weights]
                base_fields['platform']['choices'] = platforms
                base_fields['platform']['weights'] = weights

        return {
            'fields': base_fields,
            'constraints': [
                {'rule': 'original_price >= price'},
                {'rule': '1.0 <= rating <= 5.0'},
                {'rule': 'comment_count >= 0'}
            ],
            'correlations': [
                {'fields': ['rating', 'comment_count'], 'coefficient': 0.35}
            ],
            'adjustments': rules.get('adjustments', []),
            'count': count,
            'seed': seed,
            'conclusion': {
                'category': conclusion.category,
                'platform': conclusion.platform,
                'metric': conclusion.metric,
                'direction': conclusion.direction.value if conclusion.direction else None,
                'price_range': [conclusion.price_min, conclusion.price_max] if conclusion.price_min is not None else None,
                'age_range': [conclusion.demographic.age_min, conclusion.demographic.age_max],
                'gender_ratio': {'male': conclusion.demographic.male_ratio, 'female': conclusion.demographic.female_ratio},
                'regions': conclusion.regions,
                'confidence': conclusion.confidence
            }
        }


# 便捷函数
def generate_from_conclusion(conclusion_text: str, count: int = 1000, seed: int = None) -> Tuple[Dict[str, Any], str]:
    """根据结论生成数据配置

    Args:
        conclusion_text: 结论语句
        count: 数据量
        seed: 随机种子

    Returns:
        (配置字典, 解析说明)
    """
    generator = ConclusionDrivenGenerator()
    config, conclusion = generator.process(conclusion_text, count, seed)

    # 生成说明
    explanation = f"""
已解析结论:
- 品类: {conclusion.category or '未指定'}
- 平台: {conclusion.platform or '未指定'}
- 指标: {conclusion.metric or '未指定'}
- 趋势: {conclusion.direction.value if conclusion.direction else '未指定'}
- 价格: {f'{conclusion.price_min}-{conclusion.price_max}元' if conclusion.price_min is not None else '未指定'}
- 年龄: {f'{conclusion.demographic.age_min}-{conclusion.demographic.age_max}岁' if conclusion.demographic.age_min != 18 or conclusion.demographic.age_max != 60 else '未指定'}
- 性别: {f'男{conclusion.demographic.male_ratio:.0%} 女{conclusion.demographic.female_ratio:.0%}' if conclusion.demographic.male_ratio != 0.5 else '未指定'}
- 地区: {', '.join(conclusion.regions[:8]) + ('...' if len(conclusion.regions)>8 else '') if conclusion.regions else '未指定'}
- 置信度: {conclusion.confidence:.0%}

数据将生成 {count} 条记录，支持以上结论。
"""
    return config, explanation
