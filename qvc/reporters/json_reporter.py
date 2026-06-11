"""JSON 报告生成器"""

import json
from pathlib import Path
from qvc.models.report import Report
from .base import BaseReporter


class JSONReporter(BaseReporter):
    """JSON 格式报告生成器"""

    def generate(self, report: Report, output_path: Path | None = None) -> str:
        content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

        if output_path:
            output_path.write_text(content, encoding="utf-8")

        return content

    def get_extension(self) -> str:
        return ".json"
