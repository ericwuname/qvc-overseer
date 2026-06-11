# QVC vs AI Self-Review — Hard Data Comparison

> Test date: 2026-06-11 | QVC v0.6.5 | Project: ai-corp V7.1 (120 files / 19,705 lines)

## Method

1. AI Agent (Codex CLI) performs self-review on ai-corp V7.1
2. QVC scans the same project
3. Cross-validate: AI findings vs QVC findings
4. Calculate AI miss rate

## Results

| Metric | AI Self-Review | QVC External Review | Difference |
|--------|:-----------:|:---------:|:----:|
| Issues found | 0 | 4 | QVC +4 |
| High-confidence (>=90%) | 0 | 1 | QVC +1 |
| Cross-file consistency | 0 | 1 | QVC +1 |
| Boundary conditions | 0 | 2 | QVC +2 |
| Blindspot coverage | N/A | 3/3 types | QVC all |

## QVC's 4 Findings

### Bug #1 [90%] create_session() signature mismatch (22 call sites)
- **Type**: Cross-file consistency (CONTEXT_LOST)
- **Can AI see it?**: NO — signature spread across 2 files
- **Impact**: Runtime TypeError on 3-param call vs 1-param definition

### Bug #2 [85%] Silent exception swallowing (23 sites)
- **Type**: Boundary condition (BOUNDARY_CONDITION)
- **Can AI see it?**: NO — AI treats exception handlers as "handled"

### Bug #3 [85%] _deep_dive_single() insufficient arguments
- **Type**: Memory residue (MEMORY_TRAP)
- **Can AI see it?**: NO — AI remembers defining the params, skips re-check

### Bug #4 [85%] parseInt() missing radix (4 sites)
- **Type**: Boundary condition
- **Can AI see it?**: NO — subtle JS behavior rarely flagged by AI

## AI Miss Rate

`
AI self-review miss rate = 100%
(AI found 0 real issues, QVC found 4)
`

## Why AI Can't See These

| Blindspot | Mechanism | QVC Advantage |
|-----------|-----------|---------------|
| **CONTEXT_LOST** | AI reviews file A, forgot file B | QVC scans all files, builds cross-file graph |
| **MEMORY_TRAP** | Generation memory overrides review | QVC has no generation memory |
| **BOUNDARY_CONDITION** | AI checks happy path only | QVC rules target edge cases specifically |

## Conclusion

> QVC found 4 real bugs that AI self-review missed entirely. This validates the core hypothesis: **AI Agent self-review has structural blind spots, and QVC as an external overseer sits outside those blind spots.**
