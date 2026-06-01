"""
重构3：
拆分CSV输出与文件I/O工具函数于io模块。
是否应与utils模块合并？
"""

from dataclasses import asdict
import csv
from pathlib import Path

from .contracts import SettlementRow


def write_rows_to_csv(rows: list[SettlementRow], output_path: Path) -> None:
    """将结算行列表写入CSV文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))
