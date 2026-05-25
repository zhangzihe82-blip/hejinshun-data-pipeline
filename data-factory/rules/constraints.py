"""
约束规则引擎
"""
from typing import Dict, Any, List


class ConstraintEngine:
    """约束规则引擎

    管理和验证数据约束规则
    """

    def __init__(self, constraints: List[Dict[str, Any]]):
        """初始化引擎

        Args:
            constraints: 约束规则列表
        """
        self.constraints = constraints

    def validate_record(self, record: Dict[str, Any]) -> List[str]:
        """验证单条记录

        Args:
            record: 数据记录

        Returns:
            违规信息列表，空列表表示通过
        """
        violations = []

        for constraint in self.constraints:
            rule = constraint.get('rule', '')
            description = constraint.get('description', rule)

            if not self._check_rule(record, rule):
                violations.append(description)

        return violations

    def _check_rule(self, record: Dict[str, Any], rule: str) -> bool:
        """检查规则

        Args:
            record: 数据记录
            rule: 规则表达式

        Returns:
            是否通过
        """
        # original_price >= price
        if 'original_price >= price' in rule:
            price = record.get('price', 0)
            original_price = record.get('original_price')
            if original_price is None:
                return True  # 允许为空
            return original_price >= price

        # rating 范围
        if '1.0 <= rating <= 5.0' in rule:
            rating = record.get('rating')
            if rating is None:
                return True
            return 1.0 <= rating <= 5.0

        # comment_count 非负
        if 'comment_count >= 0' in rule:
            comment_count = record.get('comment_count', 0)
            return comment_count >= 0

        return True

    def fix_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """修正违规数据

        Args:
            record: 数据记录

        Returns:
            修正后的记录
        """
        fixed = record.copy()

        # 修正 original_price < price
        if fixed.get('original_price') is not None:
            if fixed['original_price'] < fixed.get('price', 0):
                fixed['original_price'] = round(fixed['price'] * 1.1, 2)

        # 修正 rating 范围
        if fixed.get('rating') is not None:
            fixed['rating'] = max(1.0, min(5.0, fixed['rating']))

        # 修正 comment_count
        if fixed.get('comment_count', 0) < 0:
            fixed['comment_count'] = 0

        return fixed
