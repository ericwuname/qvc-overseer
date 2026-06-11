# QVC Project Execution Guide

## Development Philosophy

1. **Signal over noise**: Fewer trustworthy bugs > many dubious warnings
2. **External overseer**: Never modify code, preserve independence
3. **2-minute to value**: First scan must produce useful output in <2 min
4. **Eat your own dogfood**: QVC scans itself before every release

## Version Pipeline

`
alpha → stable → beta → release
  │        │        │       │
  │        │        │       └── PyPI publish
  │        │        └── External user validation
  │        └── Hit rate verification on 5 projects
  └── Internal development + self-scan
`

## Quality Gates

| Gate | Criterion | Must Pass |
|------|-----------|:---------:|
| **Self-scan** | QVC scans itself, all >=90% verified | Yes |
| **Hit rate** | >=85% at >=90% confidence on 5 projects | Yes |
| **Regression** | All regression tests pass (45+ tests) | Yes |
| **Beta feedback** | 3 external users, no "just another linter" reaction | Yes |
| **PyPI install** | pip install qvc-overseer works on clean env | Yes |
| **CI green** | GitHub Actions workflow passes | Yes |

## Adding a New Rule

1. Create qvc/rules/<language>/<rule_name>.py
2. Subclass BaseRule, implement check(node, context)
3. Register in qvc/rules/registry.py
4. Add regression test in 	ests/
5. Run qvc scan . on a real project to verify

## Adding a New Language

1. Create qvc/rules/<language>/ with __init__.py
2. Add at least 1 rule (e.g., nil safety for Go)
3. Register language in qvc/scanner/file_scanner.py
4. Add test fixtures in 	ests/fixtures/sample_bugs_<lang>/

## Release Checklist

- [ ] Version bumped in pyproject.toml AND qvc/__init__.py
- [ ] CHANGELOG.md updated
- [ ] Self-scan passes (qvc scan .)
- [ ] Regression tests pass (pytest)
- [ ] Wheel builds (python -m build --wheel)
- [ ] PyPI upload succeeds
- [ ] pip install qvc-overseer from clean env works
- [ ] GitHub Actions CI passes
- [ ] qvc --version shows correct version

## Project Structure

See docs/QVC_Project_Report_EN.md for full architecture diagram.
