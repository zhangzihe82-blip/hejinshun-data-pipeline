"""
JSON输出器
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class JSONWriter:
    """JSON输出器"""

    def write(self, data: List[Dict[str, Any]], output_path: Path):
        """写入JSON文件

        Args:
            data: 数据列表
            output_path: 输出路径
        """
        # 转换数据
        output_data = {
            'generated_at': datetime.now().isoformat(),
            'total_records': len(data),
            'records': data
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
