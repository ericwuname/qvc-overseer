"""SARIF Reporter for VS Code / GitHub Code Scanning"""

import json
from pathlib import Path
from datetime import datetime, timezone

from qvc.models.report import Report
from qvc.models.bug import Severity
from qvc import __version__
from .base import BaseReporter


class SARIFReporter(BaseReporter):
    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
    SARIF_VERSION = "2.1.0"

    SEVERITY_MAP = {
        Severity.FATAL: "error",
        Severity.SEVERE: "error",
        Severity.MODERATE: "warning",
        Severity.MINOR: "note",
    }

    def get_extension(self):
        return ".sarif"

    def generate(self, report: Report, output_path: Path, **kwargs):
        sarif = self._build_sarif(report)
        out = Path(str(output_path) + ".sarif")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2, ensure_ascii=False)
        return out

    def _build_sarif(self, report: Report):
        runs = []
        tool = self._build_tool()
        results = self._build_results(report)
        if results:
            runs.append({
                "tool": tool,
                "results": results,
                "invocations": [{
                    "executionSuccessful": True,
                    "startTimeUtc": report.generated_at.isoformat(),
                }],
            })
        return {"$schema": self.SARIF_SCHEMA, "version": self.SARIF_VERSION, "runs": runs}

    def _build_tool(self):
        rules = []
        try:
            from qvc.rules.registry import registry
            for r in list(registry._rules.values()):
                rules.append({"id": r.rule_id, "name": r.name, "shortDescription": {"text": r.description}})
        except Exception:
            pass
        return {"driver": {"name": "QVC", "fullName": "QA of Vebe Coding",
                "version": __version__, "informationUri": "https://github.com/ericwuname/qvc-overseer", "rules": rules}}

    def _build_results(self, report: Report):
        results = []
        for bug in report.bugs:
            result = {
                "ruleId": bug.rule_id,
                "level": self.SEVERITY_MAP.get(bug.severity, "warning"),
                "message": {"text": bug.description or bug.title},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": bug.file_path.replace("\\", "/")},
                    "region": {"startLine": bug.line_start, "endLine": bug.line_end or bug.line_start},
                }}],
                "properties": {"confidence": bug.confidence},
            }
            if bug.fix_suggestion:
                result["fixes"] = [{"description": {"text": bug.fix_suggestion}}]
            results.append(result)
        return results
