"""硬编码密钥检测规则 — 跨语言通用 — Layer 1 (CERTIFICATE, 95%)"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class HardcodedSecretsRule(BaseRule):
    rule_id = "UNI_HARDCODED_SECRETS_001"
    name = "硬编码密钥检测"
    description = "检测源代码中硬编码的API密钥、密码、Token等敏感信息"
    severity = Severity.FATAL
    category = BugCategory.SECURITY
    languages = ["*"]
    layer = RuleLayer.CERTIFICATE
    base_confidence = 0.95

    # 高危模式
    PATTERNS = [
        # API 密钥
        (r'(?:api[_-]?key|apikey|api[_-]?secret|access[_-]?key|secret[_-]?key)\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})["\']',
         "API 密钥", 0.98),
        # OpenAI/Anthropic 等特定格式
        (r'(?:openai|anthropic|cohere|huggingface)[_-]?(?:api[_-]?key)\s*[:=]\s*["\'](sk-[A-Za-z0-9_\-]{20,})["\']',
         "AI 服务 API 密钥", 0.99),
        (r'(?:sk|pk|whsec)_[A-Za-z0-9_\-]{20,}',
         "Stripe/OpenAI 格式密钥", 0.95),
        # 密码
        (r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']',
         "硬编码密码", 0.95),
        # JWT/Auth Token
        (r'(?:jwt[_-]?secret|auth[_-]?token|jwt[_-]?key)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{16,}["\']',
         "JWT/Auth 密钥", 0.96),
        # 数据库连接串
        (r'(?:database[_-]?url|db[_-]?url|mongo[_-]?uri|redis[_-]?url)\s*[:=]\s*["\'](?:mongodb|postgres|mysql|redis)://[^"\']+["\']',
         "数据库连接字符串", 0.97),
        # AWS/云凭证
        (r'(?:aws[_-]?(?:access|secret)|AZURE_[A-Z_]+|GCP_[A-Z_]+)\s*[:=]\s*["\'][A-Za-z0-9_\-/+=]{16,}["\']',
         "云服务凭证", 0.97),
        # 私钥
        (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
         "硬编码私钥", 0.99),
    ]

    # 排除的假阳性模式（配置键名/示例值）
    EXCLUDE_PATTERNS = [
        r'(?:example|sample|test|demo|placeholder|your|xxx|changeme|TODO)',
        r'os\.environ(?:\[|\.get)',
        r'process\.env',
        r'import\.meta\.env',
        r'\$\{[A-Z_]+\}',
        r'<YOUR_',
        r'your-',
    ]

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        lines = source.split("\n")

        for line_no, line in enumerate(lines, 1):
            # 跳过注释行
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("<!--"):
                continue
            if stripped.startswith("*") or stripped.startswith("/*"):
                continue

            # 检查排除模式
            if any(re.search(pat, stripped, re.IGNORECASE) for pat in self.EXCLUDE_PATTERNS):
                continue

            for pattern, desc, conf in self.PATTERNS:
                match = re.search(pattern, stripped, re.IGNORECASE)
                if match:
                    # 额外检查：值不能是变量引用
                    value = match.group(1) if match.lastindex else match.group(0)
                    if value and ("${" in value or "os.environ" in value or "process.env" in value):
                        continue

                    bugs.append(self._create_bug(
                        file_path=file_path,
                        line_start=line_no,
                        line_end=line_no,
                        title=f"硬编码{desc}",
                        description=f"源代码中发现疑似硬编码的{desc}，应使用环境变量或密钥管理服务",
                        code_snippet=stripped[:200],
                        fix_suggestion=f"将{desc}移至环境变量或 .env 文件，使用 os.environ.get() 读取",
                        root_cause=RootCause.CONFIG_DRIFT,
                        confidence=conf,
                        extra_id=f"{desc}_{line_no}",
                    ))
                    break  # 每行只报一个

        return bugs
