# QVC V7 Project Execution Guide

> Codename: "Gene Pool" | Goal: Gene pool repo + 50->150 fingerprints + community loop

## V7 Goals

| Goal | Current | V7 Target |
|------|---------|-----------|
| Fingerprints | 50 seeds | 150 |
| Gene pool repo | None | qvc-fingerprints |
| Remote sync | Local only | qvc update E2E |
| Community contribution | None | qvc contribute auto-PR |
| Quality annotation | None | ai_blindspot + verified_projects |

## Architecture

```
qvc-fingerprints/          (separate GitHub repo)
├── verified/              (human-reviewed fingerprints)
├── candidates/            (auto-generated, pending review)
├── stats.json
└── README.md

qvc/evolution/
├── syncer.py              (incremental delta sync)
├── contributor.py         (auto PR generation)
├── gene_pool.py
└── seeds/                 (built-in seeds, 50->150)
```

## Quality Gates

| Gate | Standard |
|------|----------|
| Fingerprint loading | All 150 parseable |
| Sync test | qvc update pulls remote |
| Contribute test | qvc contribute generates valid PR |
| Self-scan | >=80% hit rate at high confidence |
| Regression | All existing tests pass |
