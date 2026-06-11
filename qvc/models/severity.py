"""缺陷严重度、类别、根因、规则分层 — 数据模型"""

from enum import Enum


class Severity(Enum):
    """缺陷严重度"""
    FATAL = (1, "致命", "直接导致系统崩溃/数据丢失")
    SEVERE = (2, "严重", "影响核心功能正常运行")
    MODERATE = (3, "一般", "存在潜在风险，建议修复")
    MINOR = (4, "建议", "代码质量优化，可延后处理")

    def __init__(self, level: int, label: str, description: str):
        self.level = level
        self.label = label
        self.description = description


class BugCategory(Enum):
    """缺陷类别"""
    VAR_SCOPE = ("变量作用域", "变量未定义/作用域混乱/闭包捕获错误")
    API_MISMATCH = ("API签名不匹配", "函数定义与调用的参数不匹配")
    NULL_SAFETY = ("空值安全", "未对None/undefined做边界检查")
    DEP_CHAIN = ("依赖链断裂", "import缺失/模块路径错误/循环依赖")
    EVENT_INTEGRITY = ("事件完整性", "事件处理器缺失/绑定错误")
    ENCODING = ("编码问题", "BOM/乱码/混合编码/字符转义错误")
    REGEX_FRAGILITY = ("正则脆弱性", "正则模式可能匹配异常输入")
    ERR_HANDLING = ("异常处理", "异常被静默吞没/捕获范围过大")
    DEAD_CODE = ("死代码", "不可达代码/未使用的变量/冗余逻辑")
    CONCURRENCY = ("并发安全", "竞态条件/死锁/异步模式错误")
    RESOURCE_LEAK = ("资源泄漏", "文件未关闭/连接未释放/内存泄漏")
    SECURITY = ("安全漏洞", "SQL注入/XSS/路径遍历/硬编码密钥")
    ARCHITECTURE = ("架构风险", "循环依赖/上帝类/脆弱抽象")
    STYLE = ("代码风格", "命名不规范/格式不一致")

    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description


class RootCause(Enum):
    """缺陷根因分类"""
    COPY_PASTE = "复制粘贴导致的变量/逻辑污染"
    NO_DEFENSE = "缺少防御性编程（空值/边界未检查）"
    FRAGILE_PARSE = "脆弱的文本解析架构"
    STALE_STATE = "前后端状态同步机制不健全"
    AGENT_ISOLATION = "子Agent间缺乏协调一致性"
    TYPE_CONFUSION = "类型系统使用不当"
    ERROR_SWALLOW = "异常被静默吞没"
    RACE_CONDITION = "并发/竞态条件"
    CONFIG_DRIFT = "配置与环境不一致"


class RuleLayer:
    """规则分层"""
    _instances = {}

    def __init__(self, value: int):
        self._value = value
        RuleLayer._instances[value] = self

    @property
    def value(self) -> int:
        return self._value

    @property
    def label(self) -> str:
        labels = {1: "确定性", 2: "模式匹配", 3: "启发式推断"}
        return labels.get(self._value, "未知")

    @property
    def base_confidence(self) -> float:
        defaults = {1: 0.95, 2: 0.75, 3: 0.35}
        return defaults.get(self._value, 0.5)

    @property
    def max_severity(self):
        limits = {1: Severity.FATAL, 2: Severity.SEVERE, 3: Severity.MODERATE}
        return limits.get(self._value, Severity.MINOR)

    def __eq__(self, other):
        if isinstance(other, RuleLayer): return self._value == other._value
        if isinstance(other, int): return self._value == other
        return False

    def __hash__(self): return hash(self._value)
    def __repr__(self): return f"<RuleLayer.{self.label}>"


RuleLayer.CERTIFICATE = RuleLayer(1)
RuleLayer.PATTERN = RuleLayer(2)
RuleLayer.HEURISTIC = RuleLayer(3)