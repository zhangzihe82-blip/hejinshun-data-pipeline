"""
CSV输出器
"""
import csv
from pathlib import Path
from typing import Dict, Any, List


class CSVWriter:
    """CSV输出器"""

    COLUMN_ORDER = [
        'name', 'price', 'original_price', 'platform',
        'rating', 'comment_count', 'image_url',
        'product_url', 'category', 'scraped_at'
    ]

    def write(self, data: List[Dict[str, Any]], output_path: Path):
        """写入CSV文件

        Args:
            data: 数据列表
            output_path: 输出路径
        """
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMN_ORDER)
            writer.writeheader()
            writer.writerows(data)
