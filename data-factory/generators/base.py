"""
数据生成器基类
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import hashlib


class DataGenerator:
    """数据生成器

    根据配置生成具有统计真实性的数据
    """

    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """初始化生成器

        Args:
            config: 配置字典
            seed: 随机种子，用于可重现生成
        """
        self.config = config
        self.fields_config = config.get('fields', {})
        self.constraints = config.get('constraints', [])
        self.correlations = config.get('correlations', [])

        # 初始化随机状态
        self.rng = np.random.default_rng(seed)
        self.seed = seed

        # 唯一值追踪
        self._unique_values = set()

        # 词库
        self._init_vocabularies()

    def _init_vocabularies(self):
        """初始化中文词库"""
        self.brands = [
            '华为', '小米', '苹果', '三星', 'OPPO', 'vivo', '荣耀', 'realme',
            '美的', '格力', '海尔', 'TCL', '海信', '创维',
            '李宁', '安踏', '特步', '鸿星尔克', '361度',
            '三只松鼠', '良品铺子', '百草味', '卫龙',
            '蒙牛', '伊利', '农夫山泉', '康师傅'
        ]

        self.categories = [
            '手机', '平板电脑', '笔记本电脑', '智能手表', '耳机',
            '冰箱', '洗衣机', '空调', '电视', '热水器',
            '运动鞋', '运动服', '休闲服', '羽绒服', 'T恤',
            '零食', '坚果', '饼干', '饮料', '方便面'
        ]

        self.features = [
            '旗舰版', '尊享版', '经典款', '新款', '限量版',
            '大容量', '超薄', '智能', '变频', '静音',
            '透气', '防水', '保暖', '速干', '轻薄'
        ]

        self.suffixes = [
            '', '（官方正品）', '【爆款】', '【热销】', '【推荐】',
            '赠品丰富', '包邮', '极速发货'
        ]

    def generate(self, count: int) -> List[Dict[str, Any]]:
        """生成数据

        Args:
            count: 生成记录数量

        Returns:
            生成的数据列表
        """
        records = []

        for i in range(count):
            record = self._generate_record(i)
            if record:
                records.append(record)

        # 应用关联规则
        self._apply_correlations(records)

        # 应用约束修正
        self._apply_constraints(records)

        return records

    def _generate_record(self, index: int) -> Optional[Dict[str, Any]]:
        """生成单条记录"""
        record = {}

        for field_name, field_config in self.fields_config.items():
            value = self._generate_field(field_name, field_config, record, index)
            record[field_name] = value

        return record

    def _generate_field(self, field_name: str, config: Dict[str, Any],
                        record: Dict[str, Any], index: int) -> Any:
        """生成字段值"""
        field_type = config.get('type', 'string')
        method = config.get('method', 'choice')

        # 处理 null_probability
        null_prob = config.get('null_probability', 0)
        if null_prob > 0 and self.rng.random() < null_prob:
            return None

        if field_type == 'string':
            return self._generate_string(field_name, config, index)
        elif field_type == 'float':
            return self._generate_float(config)
        elif field_type == 'integer':
            return self._generate_integer(config)
        elif field_type == 'datetime':
            return self._generate_datetime(config)

        return None

    def _generate_string(self, field_name: str, config: Dict[str, Any], index: int) -> str:
        """生成字符串字段"""
        method = config.get('method', 'choice')

        if method == 'template':
            template = config.get('template', '')

            if '{brand}' in template:
                brand = self.rng.choice(self.brands)
                template = template.replace('{brand}', brand)

            if '{category}' in template:
                category = self.rng.choice(self.categories)
                template = template.replace('{category}', category)

            if '{feature}' in template:
                feature = self.rng.choice(self.features)
                template = template.replace('{feature}', feature)

            if '{suffix}' in template:
                suffix = self.rng.choice(self.suffixes)
                template = template.replace('{suffix}', suffix)

            if '{id}' in template:
                # 生成唯一ID
                unique_id = self._generate_unique_id(field_name, index)
                template = template.replace('{id}', unique_id)

            return template.strip()

        elif method == 'choice':
            choices = config.get('choices', ['未知'])
            weights = config.get('weights')

            if weights:
                # 确保权重总和为1.0，避免浮点精度问题
                total = sum(weights)
                if abs(total - 1.0) > 1e-10:
                    weights = [w / total for w in weights]
                return self.rng.choice(choices, p=weights)
            return self.rng.choice(choices)

        return '未知'

    def _generate_float(self, config: Dict[str, Any]) -> float:
        """生成浮点数字段"""
        method = config.get('method', 'uniform')

        if method == 'lognormal':
            mean = config.get('mean', 5.0)
            sigma = config.get('sigma', 1.0)
            value = self.rng.lognormal(mean, sigma)

        elif method == 'truncated_normal':
            mean = config.get('mean', 3.0)
            sigma = config.get('sigma', 1.0)
            min_val = config.get('min', 0)
            max_val = config.get('max', 5)

            # 生成并截断
            value = self.rng.normal(mean, sigma)
            value = max(min_val, min(max_val, value))

        elif method == 'derived':
            # 派生字段在约束阶段处理
            return 0.0

        else:  # uniform
            min_val = config.get('min', 0)
            max_val = config.get('max', 100)
            value = self.rng.uniform(min_val, max_val)

        # 应用边界
        min_val = config.get('min')
        max_val = config.get('max')
        if min_val is not None:
            value = max(min_val, value)
        if max_val is not None:
            value = min(max_val, value)

        return round(value, 2)

    def _generate_integer(self, config: Dict[str, Any]) -> int:
        """生成整数字段"""
        method = config.get('method', 'poisson')

        if method == 'poisson':
            lam = config.get('lambda', 100)
            value = self.rng.poisson(lam)

        else:  # uniform
            min_val = config.get('min', 0)
            max_val = config.get('max', 1000)
            value = self.rng.integers(min_val, max_val + 1)

        # 应用边界
        min_val = config.get('min')
        if min_val is not None:
            value = max(min_val, value)

        return int(value)

    def _generate_datetime(self, config: Dict[str, Any]) -> str:
        """生成日期时间字段"""
        start_str = config.get('start', '2024-01-01')
        end_str = config.get('end', '2024-12-31')

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        # 随机时间
        delta = end - start
        random_days = self.rng.integers(0, delta.days)
        random_seconds = self.rng.integers(0, 86400)

        dt = start + timedelta(days=int(random_days), seconds=int(random_seconds))

        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def _generate_unique_id(self, field_name: str, index: int) -> str:
        """生成唯一ID"""
        while True:
            # 使用随机数生成ID
            random_part = self.rng.integers(100000, 999999999)
            unique_id = str(random_part)

            key = f"{field_name}_{unique_id}"
            if key not in self._unique_values:
                self._unique_values.add(key)
                return unique_id

    def _apply_correlations(self, records: List[Dict[str, Any]]):
        """应用字段关联规则"""
        for correlation in self.correlations:
            fields = correlation.get('fields', [])
            coef = correlation.get('coefficient', 0)

            if len(fields) == 2 and 'rating' in fields and 'comment_count' in fields:
                # rating 与 comment_count 正相关
                for record in records:
                    rating = record.get('rating', 4.0)
                    if rating is not None:
                        # 高评分倾向于更多评论
                        base_comment = record.get('comment_count', 0)
                        adjustment = int((rating - 3.0) * 200 * coef)
                        record['comment_count'] = max(0, base_comment + adjustment)

    def _apply_constraints(self, records: List[Dict[str, Any]]):
        """应用约束规则并修正违规数据"""
        for record in records:
            for constraint in self.constraints:
                rule = constraint.get('rule', '')

                # original_price >= price
                if 'original_price >= price' in rule:
                    price = record.get('price', 0)
                    original_price = record.get('original_price')

                    if original_price is not None and original_price < price:
                        record['original_price'] = round(price * 1.1, 2)

                # 评分范围
                if 'rating' in rule:
                    rating = record.get('rating')
                    if rating is not None:
                        record['rating'] = max(1.0, min(5.0, rating))

                # 评论数非负
                if 'comment_count' in rule:
                    comment_count = record.get('comment_count', 0)
                    record['comment_count'] = max(0, comment_count)
