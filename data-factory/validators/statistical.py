"""
统计验证器
"""
import numpy as np
from scipy import stats
from typing import Dict, Any, List


class DataValidator:
    """数据验证器

    验证生成数据的统计真实性和一致性
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化验证器

        Args:
            config: 配置字典
        """
        self.config = config
        self.constraints = config.get('constraints', [])

    def validate(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证数据

        Args:
            data: 数据列表

        Returns:
            验证报告字典
        """
        report = {
            'total_records': len(data),
            'consistency_rate': 1.0,
            'uniqueness_rate': 1.0,
            'statistical_tests': {},
            'issues': [],
            'is_valid': True
        }

        if not data:
            report['issues'].append('数据为空')
            report['is_valid'] = False
            return report

        # 一致性检查
        consistency_issues = self._check_consistency(data)
        if consistency_issues:
            report['consistency_rate'] = 1 - len(consistency_issues) / len(data)
            report['issues'].extend(consistency_issues[:20])

        # 唯一性检查
        uniqueness_issues = self._check_uniqueness(data)
        if uniqueness_issues:
            report['uniqueness_rate'] = 1 - len(uniqueness_issues) / len(data)
            report['issues'].extend(uniqueness_issues[:10])

        # 统计检验
        report['statistical_tests'] = self._statistical_tests(data)

        # 判断整体有效性
        report['is_valid'] = (
            report['consistency_rate'] >= 0.95 and
            report['uniqueness_rate'] >= 0.99
        )

        return report

    def _check_consistency(self, data: List[Dict[str, Any]]) -> List[str]:
        """检查数据一致性"""
        issues = []

        for i, record in enumerate(data):
            # 检查 name 非空
            if not record.get('name'):
                issues.append(f"记录 {i+1}: name 为空")

            # 检查 original_price >= price
            price = record.get('price', 0)
            original_price = record.get('original_price')
            if original_price is not None and original_price < price:
                issues.append(f"记录 {i+1}: original_price ({original_price}) < price ({price})")

            # 检查评分范围
            rating = record.get('rating')
            if rating is not None and (rating < 1.0 or rating > 5.0):
                issues.append(f"记录 {i+1}: rating ({rating}) 超出范围 [1, 5]")

            # 检查评论数非负
            comment_count = record.get('comment_count', 0)
            if comment_count < 0:
                issues.append(f"记录 {i+1}: comment_count ({comment_count}) 为负数")

        return issues

    def _check_uniqueness(self, data: List[Dict[str, Any]]) -> List[str]:
        """检查唯一性"""
        issues = []

        # 检查 product_url 唯一性
        urls = [r.get('product_url') for r in data if r.get('product_url')]
        unique_urls = set(urls)

        if len(urls) != len(unique_urls):
            duplicate_count = len(urls) - len(unique_urls)
            issues.append(f"发现 {duplicate_count} 个重复的 product_url")

        return issues

    def _statistical_tests(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """统计检验"""
        results = {}

        # 提取数值字段
        prices = [r.get('price') for r in data if r.get('price') is not None]
        ratings = [r.get('rating') for r in data if r.get('rating') is not None]
        comments = [r.get('comment_count') for r in data if r.get('comment_count') is not None]

        # 价格分布检验（对数正态）
        if prices and len(prices) >= 30:
            log_prices = np.log(prices)
            # Shapiro-Wilk 正态检验
            stat, p_value = stats.shapiro(log_prices[:min(5000, len(log_prices))])
            results['price_lognormal'] = {
                'test': 'shapiro-wilk',
                'statistic': float(stat),
                'p_value': float(p_value),
                'is_normal': p_value > 0.05
            }

        # 评分分布检验（截断正态）
        if ratings and len(ratings) >= 30:
            stat, p_value = stats.normaltest(ratings)
            results['rating_normal'] = {
                'test': "D'Agostino-Pearson",
                'statistic': float(stat),
                'p_value': float(p_value),
                'is_normal': p_value > 0.05
            }

        # 相关性检验
        if ratings and comments and len(ratings) == len(comments):
            if len(ratings) >= 10:
                corr, p_value = stats.pearsonr(ratings, comments)
                results['rating_comment_correlation'] = {
                    'correlation': float(corr),
                    'p_value': float(p_value),
                    'is_significant': p_value < 0.05
                }

        return results
