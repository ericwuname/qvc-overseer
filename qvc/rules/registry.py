"""规则注册中心 —— 管理所有审查规则的加载与分发"""

from pathlib import Path
from .base import BaseRule


class RuleRegistry:
    """规则注册中心"""

    def __init__(self):
        self._rules: dict[str, BaseRule] = {}
        self._rules_by_language: dict[str, list[BaseRule]] = {}

    def register(self, rule: BaseRule):
        """注册一条规则"""
        if rule.rule_id in self._rules:
            raise ValueError(f"规则ID重复: {rule.rule_id}")
        self._rules[rule.rule_id] = rule
        for lang in rule.languages:
            self._rules_by_language.setdefault(lang.lower(), []).append(rule)

    def register_many(self, rules: list[BaseRule]):
        """批量注册规则"""
        for rule in rules:
            self.register(rule)

    def get_rule(self, rule_id: str) -> BaseRule | None:
        """根据ID获取规则"""
        return self._rules.get(rule_id)

    def get_rules_for_language(self, language: str) -> list[BaseRule]:
        """获取适用于指定语言的所有规则"""
        return self._rules_by_language.get(language.lower(), [])

    def get_rules_by_ids(self, rule_ids: list[str]) -> list[BaseRule]:
        """根据ID列表获取规则"""
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def get_all_rules(self) -> list[BaseRule]:
        """获取所有规则"""
        return list(self._rules.values())

    def get_rule_ids(self) -> list[str]:
        """获取所有规则ID"""
        return list(self._rules.keys())

    def filter_rules(
        self,
        languages: list[str] | None = None,
        rule_ids: list[str] | None = None,
        exclude_ids: list[str] | None = None,
    ) -> list[BaseRule]:
        """按条件筛选规则"""
        rules = self.get_all_rules()

        if languages:
            lang_set = {l.lower() for l in languages}
            rules = [r for r in rules if any(
                l.lower() in lang_set for l in r.languages
            )]

        if rule_ids:
            id_set = set(rule_ids)
            rules = [r for r in rules if r.rule_id in id_set]

        if exclude_ids:
            ex_set = set(exclude_ids)
            rules = [r for r in rules if r.rule_id not in ex_set]

        return rules

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:
        return f"<RuleRegistry({self.rule_count} rules)>"


# 全局注册中心
registry = RuleRegistry()
