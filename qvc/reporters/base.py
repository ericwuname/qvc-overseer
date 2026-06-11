"""报告生成器基类"""

from abc import ABC, abstractmethod
from pathlib import Path
from qvc.models.report import Report


class BaseReporter(ABC):
    """报告生成器基类"""

    @abstractmethod
    def generate(self, report: Report, output_path: Path | None = None) -> str:
        """生成报告，返回报告内容字符串"""
        ...

    @abstractmethod
    def get_extension(self) -> str:
        """返回报告文件扩展名"""
        ...
