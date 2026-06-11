# QVC Project Retrospective

> V1 → V6.1 | From idea to PyPI | 7 major versions

## Key Numbers

| Metric | Value |
|--------|-------|
| Versions | 7 (V1-V6.1) |
| Code size | ~8,000 lines Python |
| CLI commands | 13 |
| Languages supported | 5 |
| Regression tests | 45+ |
| AI miss rate detected | 100% (4/4 bugs) |
| High-confidence hit rate | 100% @ >=90% |

## 5 Critical Pivots

1. **"Better linter" → "External overseer"**: Found unique positioning
2. **"Auto-fix bugs" → "Never modify code"**: Preserved externality moat
3. **"281 bugs→0 bugs" → "Signal priority"**: Three-layer confidence engine
4. **"Sell premium" → "Free, earn trust"**: Quality builds adoption
5. **"Add Go+Rust" → "Cut scope, verify trust"**: 40% time saved

## 5 Failures & Root Causes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | Confidence not working (V1) | No signal layering | 3-layer engine |
| 2 | PyPI name collision | No pre-flight check | Renamed to qvc-overseer |
| 3 | CI workflow broken | Referenced non-existent action | pip install instead |
| 4 | Version desync | Two files, single source of truth broken | Manual sync |
| 5 | Test fixtures pollute results | No self-scan exclusion | Added fixtures/ to exclude |

## 5 Reusable Patterns

1. **Contradiction-driven decisions**: Build tension → extreme constraint → breakthrough
2. **Alpha→Stable→Beta pipeline**: Internal trust → code confidence → user trust
3. **External feedback loop**: Each version reviewed externally before next iteration
4. **"2-minute to value" filter**: Every feature decision: "Without it, does first scan produce value?"
5. **Dogfood first**: QVC scans itself before every release

## One-Sentence Summary

> It's not that QVC has better rules. It's that QVC sits **outside** the AI Agent's cognitive loop — and that positional advantage is the real moat.
