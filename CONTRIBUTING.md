# Contributing to QVC

> QVC is an open-source project. We welcome contributions from developers worldwide.
> [中文贡献指南](docs/QVC_用户使用手册.md) | English below

## Quick Start

`ash
git clone https://github.com/ericwuname/qvc-overseer.git
cd qvc-overseer
pip install -e ".[dev]"
`

## Ways to Contribute

| Area | What | Impact |
|------|------|--------|
| **Rules** | New detection rules for Python/JS/TS/React/Go | Broader coverage |
| **Fingerprints** | Bug patterns you've discovered in real projects | Stronger gene pool |
| **Documentation** | Fixes, translations (especially English + Chinese) | Better onboarding |
| **Bug fixes** | Report issues or submit PRs | Reliability |
| **Translations** | Translate docs to your language | Global reach |

## Adding a Rule

1. Create file in qvc/rules/<language>/
2. Subclass BaseRule, implement check(node, context)
3. Register in qvc/rules/registry.py
4. Add regression test
5. Submit PR

`python
from qvc.rules.base import BaseRule

class MyRule(BaseRule):
    name = "my_rule"
    description = "Detects XYZ pattern"
    confidence = 85
    blindspot = "boundary_condition"

    def check(self, node, context):
        if "dangerous_pattern" in node.text:
            return self.bug(node, "Found dangerous pattern")
`

## Contributing Fingerprints

`ash
qvc contribute  # Submit local fingerprints
`

Or manually add to qvc/evolution/seeds/ and open a PR.

## Development

`ash
pytest tests/ -v          # Run all tests
qvc scan . --full         # Self-test (eat your own dogfood)
python -m build --wheel   # Build package
`

## PR Checklist

- [ ] Tests pass (pytest)
- [ ] Self-scan clean (qvc scan .)
- [ ] CHANGELOG.md updated
- [ ] No BOM in new files
- [ ] English comments/docstrings (codebase language is English)

## Code of Conduct

Be respectful. Focus on code quality. QVC reviews code — not people.

## Questions?

Open an issue on [GitHub](https://github.com/ericwuname/qvc-overseer/issues).
