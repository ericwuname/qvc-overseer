"""配置管理 V2 —— 支持 YAML 配置文件"""

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    enabled: bool = False
    model: str = "gpt-5.2"
    provider: str = "openai"  # openai | local (Ollama) | custom (DeepSeek/Qwen/etc)
    api_key: str | None = None
    base_url: str | None = None
    max_files: int = 20


@dataclass
class EvolutionConfig:
    auto_evolve: bool = False
    min_gap_cluster: int = 2


@dataclass
class ScanConfig:
    """扫描配置"""
    target: str = "."
    output: str = "qvc-report"
    formats: list[str] = field(default_factory=lambda: ["markdown"])
    languages: list[str] | None = None
    include_languages: list[str] | None = None
    rules: list[str] | None = None
    enable_rules: list[str] | None = None
    disable_rules: list[str] | None = None
    exclude_rules: list[str] | None = None
    exclude_dirs: list[str] | None = None
    min_severity: str = "minor"
    llm: LLMConfig = field(default_factory=LLMConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    max_workers: int = 4
    quiet: bool = False

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ScanConfig":
        """从 YAML 配置文件加载"""
        try:
            import yaml
        except ImportError:
            raise ImportError("需要 PyYAML: pip install pyyaml")

        if not yaml_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        # 基础字段
        for key in ["target", "output", "min_severity", "max_workers", "quiet"]:
            if key in data:
                setattr(config, key, data[key])

        # 列表字段
        for key in ["formats", "languages", "include_languages",
                     "rules", "enable_rules", "disable_rules",
                     "exclude_rules", "exclude_dirs"]:
            if key in data:
                setattr(config, key, data[key])

        # LLM 配置
        if "llm" in data:
            llm_data = data["llm"]
            config.llm = LLMConfig(
                enabled=llm_data.get("enabled", False),
                model=llm_data.get("model", "gpt-5.2"),
                api_key=llm_data.get("api_key"),
                base_url=llm_data.get("base_url"),
                max_files=llm_data.get("max_files", 20),
            )

        # 进化引擎配置
        if "evolution" in data:
            evo_data = data["evolution"]
            config.evolution = EvolutionConfig(
                auto_evolve=evo_data.get("auto_evolve", False),
                min_gap_cluster=evo_data.get("min_gap_cluster", 2),
            )

        return config

    @classmethod
    def from_env(cls, **overrides) -> "ScanConfig":
        """从环境变量和 CLI 参数创建（兼容旧接口）"""
        config = cls()
        config.llm.api_key = os.environ.get("OPENAI_API_KEY")
        config.llm.base_url = os.environ.get("OPENAI_BASE_URL")
        for key, value in overrides.items():
            if value is not None:
                if key.startswith("llm_"):
                    llm_key = key[4:]  # llm_model -> model
                    if hasattr(config.llm, llm_key):
                        setattr(config.llm, llm_key, value)
                elif key.startswith("evo_"):
                    evo_key = key[4:]
                    if hasattr(config.evolution, evo_key):
                        setattr(config.evolution, evo_key, value)
                elif hasattr(config, key):
                    setattr(config, key, value)
        return config

    @classmethod
    def auto_load(cls, target_path: Path | None = None, **cli_overrides) -> "ScanConfig":
        """自动加载：优先 CLI > YAML > 默认值"""
        import os

        # 1. 查找 YAML 配置文件
        yaml_path = None

        # CLI 指定的配置文件
        if "config" in cli_overrides and cli_overrides["config"]:
            yaml_path = Path(cli_overrides["config"])
            del cli_overrides["config"]

        # 自动发现：当前目录 / 项目根目录
        if yaml_path is None and target_path:
            search_dirs = [target_path]
            cwd = Path.cwd()
            if cwd != target_path:
                search_dirs.append(cwd)
            for d in search_dirs:
                candidate = d / "qvc.yaml" if d.is_dir() else d.parent / "qvc.yaml"
                if candidate.exists():
                    yaml_path = candidate
                    break

        # 2. 加载 YAML（如果存在）
        if yaml_path and yaml_path.exists():
            try:
                config = cls.from_yaml(yaml_path)
            except Exception:
                config = cls()
        else:
            config = cls()

        # 3. CLI 参数覆盖
        config.llm.api_key = cli_overrides.pop("llm_api_key", None) or os.environ.get("OPENAI_API_KEY")
        config.llm.base_url = cli_overrides.pop("llm_base_url", None) or os.environ.get("OPENAI_BASE_URL")

        for key, value in list(cli_overrides.items()):
            if value is not None:
                if key.startswith("llm_") and hasattr(config.llm, key[4:]):
                    setattr(config.llm, key[4:], value)
                elif key.startswith("evo_") and hasattr(config.evolution, key[4:]):
                    setattr(config.evolution, key[4:], value)
                elif hasattr(config, key):
                    setattr(config, key, value)

        return config

    def get_effective_rules(self) -> tuple[list[str] | None, list[str] | None]:
        """获取生效的规则配置：优先 enable_rules > rules，优先 disable_rules > exclude_rules"""
        include = self.enable_rules or self.rules
        exclude = self.disable_rules or self.exclude_rules
        return include, exclude

    def get_effective_languages(self) -> list[str] | None:
        return self.languages or self.include_languages
