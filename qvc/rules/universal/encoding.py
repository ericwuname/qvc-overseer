"""编码检测规则 —— 跨语言通用"""

from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class EncodingCheckRule(BaseRule):
    rule_id = "UNI_ENCODING_001"
    name = "文件编码检测"
    description = "检测 BOM 字符、混合编码、非 UTF-8 文件"
    severity = Severity.SEVERE
    category = BugCategory.ENCODING
    languages = ["*"]  # 全部语言
    layer = RuleLayer.CERTIFICATE  # base_confidence = 0.99

    # BOM 字节序
    BOM_UTF8 = b'\xef\xbb\xbf'
    BOM_UTF16_LE = b'\xff\xfe'
    BOM_UTF16_BE = b'\xfe\xff'
    BOM_UTF32_LE = b'\xff\xfe\x00\x00'
    BOM_UTF32_BE = b'\x00\x00\xfe\xff'

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        try:
            raw_bytes = file_path.read_bytes()
        except (OSError, PermissionError):
            return bugs

        # 检测 BOM
        bom_found = None
        if raw_bytes.startswith(self.BOM_UTF8):
            bom_found = "UTF-8 BOM"
        elif raw_bytes.startswith(self.BOM_UTF16_LE):
            bom_found = "UTF-16 LE BOM"
        elif raw_bytes.startswith(self.BOM_UTF16_BE):
            bom_found = "UTF-16 BE BOM"
        elif raw_bytes.startswith(self.BOM_UTF32_LE):
            bom_found = "UTF-32 LE BOM"
        elif raw_bytes.startswith(self.BOM_UTF32_BE):
            bom_found = "UTF-32 BE BOM"

        if bom_found:
            bugs.append(self._create_bug(
                file_path=file_path,
                line_start=1,
                line_end=1,
                title=f"文件包含 {bom_found} 字符",
                description=f"文件头部包含 {bom_found}，可能导致 JSON 解析失败或前端构建报错",
                fix_suggestion=f"使用 'Save as UTF-8 without BOM' 重新保存文件",
                root_cause=RootCause.CONFIG_DRIFT,
                confidence=0.95,
                extra_id="BOM",
            ))

        # 检测无效 UTF-8
        try:
            raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            bugs.append(self._create_bug(
                file_path=file_path,
                line_start=1,
                line_end=1,
                title="文件编码不是有效的 UTF-8",
                description="文件包含无法以 UTF-8 解码的字节，可能使用 GBK/Shift-JIS 等编码",
                fix_suggestion="将文件转换为 UTF-8 编码",
                root_cause=RootCause.CONFIG_DRIFT,
                confidence=0.9,
                extra_id="ENCODING",
            ))

        return bugs

    def supports_language(self, language: str) -> bool:
        return True  # 对所有语言生效
