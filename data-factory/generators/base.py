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
        # 品牌按品类分组
        self.brands_by_category = {
            # 漆器品类 - 中国传统漆器产地/品牌
            '漆器': [
                '福州脱胎漆器', '扬州漆器', '北京雕漆', '成都漆器', '平遥推光漆器',
                '天水雕漆', '厦门漆线雕', '阳江漆器', '金漆镶嵌', '鄱阳脱胎漆器',
                '宜春脱胎漆器', '重庆漆器', '苏州漆器', '宁波漆器', '温州漆器',
                '徽州漆器', '楚式漆器', '漆艺工坊', '国漆坊', '漆道'
            ],
            '手机': ['华为', '小米', '苹果', '三星', 'OPPO', 'vivo', '荣耀', 'realme', '一加', '魅族'],
            '电脑': ['联想', '戴尔', '惠普', '华硕', '苹果', '华为', '小米', '宏碁', '机械革命'],
            '家电': ['美的', '格力', '海尔', 'TCL', '海信', '创维', '西门子', '松下', '索尼'],
            '服装': ['李宁', '安踏', '特步', '鸿星尔克', '361度', '优衣库', 'ZARA', 'H&M'],
            '食品': ['三只松鼠', '良品铺子', '百草味', '卫龙', '蒙牛', '伊利', '农夫山泉', '康师傅'],
            '图书': ['人民文学', '机械工业', '清华', '北大', '中信', '电子工业'],
            '美妆': ['兰蔻', '雅诗兰黛', 'SK-II', '资生堂', '欧莱雅', '完美日记', '花西子'],
            '家居': ['宜家', '全友', '顾家', '林氏木业', '喜临门', '芝华仕'],
            '数码': ['索尼', '佳能', '尼康', '大疆', 'Bose', 'JBL', '漫步者', '森海塞尔'],
        }

        # 默认品牌列表（兼容旧逻辑）
        self.brands = []
        for brands in self.brands_by_category.values():
            self.brands.extend(brands)

        # 子品类按主品类分组（用于生成商品名称）
        self.subcategories = {
            # 漆器子品类 - 漆器产品类型
            '漆器': [
                '漆器首饰盒', '漆器茶盘', '漆器茶具套装', '漆器花瓶', '漆器果盘',
                '漆器屏风', '漆器笔筒', '漆器文房四宝', '漆器印泥盒', '漆器首饰',
                '漆器梳妆盒', '漆器收纳盒', '漆器烟盒', '漆器棋盒', '漆器茶叶罐',
                '漆器餐具套装', '漆器碗', '漆器筷子', '漆器托盘', '漆器摆件',
                '漆器挂屏', '漆器砚台盒', '漆器卷轴盒', '漆器香盒', '漆器佛珠盒'
            ],
            '手机': ['智能手机', '折叠屏手机', '游戏手机', '5G手机', '拍照手机'],
            '电脑': ['笔记本电脑', '台式电脑', '游戏本', '轻薄本', '一体机'],
            '家电': ['冰箱', '洗衣机', '空调', '电视', '热水器', '微波炉', '电饭煲'],
            '服装': ['T恤', '衬衫', '外套', '裤子', '连衣裙', '羽绒服', '运动鞋'],
            '食品': ['坚果', '零食', '饼干', '饮料', '牛奶', '方便面', '巧克力'],
            '图书': ['小说', '散文', '传记', '科技', '教育', '历史', '艺术'],
            '美妆': ['口红', '粉底', '眼影', '面膜', '精华', '洗面奶', '防晒霜'],
            '家居': ['沙发', '床', '床垫', '餐桌', '衣柜', '书桌', '茶几'],
            '数码': ['耳机', '相机', '智能手表', '平板', '无人机', '音箱', '投影仪'],
        }

        self.categories = list(self.brands_by_category.keys())

        # 漆器专用特性
        self.lacquerware_features = [
            '手工雕刻', '天然大漆', '螺甸镶嵌', '蛋壳镶嵌', '金箔贴饰',
            '推光漆', '雕漆工艺', '脱胎工艺', '描金工艺', '戗金工艺',
            '彩绘漆', '磨漆画', '堆漆', '填漆', '罩漆',
            '仿古做旧', '现代简约', '中式古典', '礼品装', '收藏级',
            '黑檀底', '红木底', '楠木底', '榫卯结构', '手工打磨'
        ]

        self.features = [
            '旗舰版', '尊享版', '经典款', '新款', '限量版',
            '大容量', '超薄', '智能', '变频', '静音',
            '透气', '防水', '保暖', '速干', '轻薄',
            '高清', '4K', '电竞', '游戏', '商务'
        ]

        self.suffixes = [
            '', '（官方正品）', '【爆款】', '【热销】', '【推荐】',
            '赠品丰富', '包邮', '极速发货', '品质保证',
            '非遗传承', '大师监制', '手工制作', '送礼佳品', '收藏臻品'
        ]

        # 用户指定的主品类（从结论中提取）
        self.user_category = None

    def generate(self, count: int) -> List[Dict[str, Any]]:
        """生成数据

        Args:
            count: 生成记录数量

        Returns:
            生成的数据列表
        """
        # 提取用户指定的主品类
        category_config = self.fields_config.get('category', {})
        category_choices = category_config.get('choices', [])
        category_weights = category_config.get('weights', [])

        # 如果权重集中在某个品类，则设置用户品类
        if category_weights and max(category_weights) > 0.5:
            max_idx = category_weights.index(max(category_weights))
            if max_idx < len(category_choices):
                self.user_category = category_choices[max_idx]

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
                # 优先使用用户品类对应的品牌
                if self.user_category and self.user_category in self.brands_by_category:
                    brand = self.rng.choice(self.brands_by_category[self.user_category])
                else:
                    brand = self.rng.choice(self.brands)
                template = template.replace('{brand}', brand)

            if '{category}' in template:
                # 生成商品名称时使用子品类
                if self.user_category and self.user_category in self.subcategories:
                    subcategory = self.rng.choice(self.subcategories[self.user_category])
                else:
                    subcategory = self.rng.choice(self.categories)
                template = template.replace('{category}', subcategory)

            if '{feature}' in template:
                # 漆器使用专用特性词库
                if self.user_category == '漆器':
                    feature = self.rng.choice(self.lacquerware_features)
                else:
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
        min_val = config.get('min')
        max_val = config.get('max')

        if method == 'lognormal':
            mean = config.get('mean', 5.0)
            sigma = config.get('sigma', 1.0)

            # 如果指定了min和max，使用拒绝采样确保值在范围内
            if min_val is not None and max_val is not None:
                max_attempts = 100
                for _ in range(max_attempts):
                    value = self.rng.lognormal(mean, sigma)
                    if min_val <= value <= max_val:
                        break
                else:
                    # 如果多次尝试都失败，使用均匀分布
                    value = self.rng.uniform(min_val, max_val)
            else:
                value = self.rng.lognormal(mean, sigma)

        elif method == 'truncated_normal':
            mean = config.get('mean', 3.0)
            sigma = config.get('sigma', 1.0)
            t_min = config.get('min', 0)
            t_max = config.get('max', 5)

            # 生成并截断
            value = self.rng.normal(mean, sigma)
            value = max(t_min, min(t_max, value))

        elif method == 'derived':
            # 派生字段在约束阶段处理
            return 0.0

        else:  # uniform
            if min_val is not None and max_val is not None:
                value = self.rng.uniform(min_val, max_val)
            else:
                value = self.rng.uniform(0, 100)

        # 应用边界
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
