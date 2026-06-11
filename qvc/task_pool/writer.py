"""Task Pool Writer — converts QVC bugs into AI-consumable task files."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List


class TaskPoolWriter:
    """Writes QVC-discovered bugs to .qvc/tasks/pending.md with metadata."""

    MIN_CONFIDENCE = 0.70
    MAX_TASKS = 5
    TASKS_DIR = ".qvc/tasks"

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.tasks_dir = self.project_root / self.TASKS_DIR
        self.pending_path = self.tasks_dir / "pending.md"
        self.status_path = self.tasks_dir / "status.json"
        self.history_path = self.tasks_dir / "history.md"

    def ensure_dir(self):
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def load_status(self) -> dict:
        if self.status_path.exists():
            try:
                with open(self.status_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def save_status(self, status: dict):
        self.ensure_dir()
        with open(self.status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

    def generate_task_id(self, date_str: str, idx: int) -> str:
        return f"QVC-{date_str}-{idx:03d}"

    def write_pending(self, bugs, project_name: str = "") -> int:
        """Write actionable bugs to pending.md. Returns number of tasks written."""
        from qvc.models.bug import Bug

        self.ensure_dir()

        # Filter: confidence >= MIN_CONFIDENCE
        actionable = [b for b in bugs if b.confidence >= self.MIN_CONFIDENCE]
        if not actionable:
            if self.pending_path.exists():
                self.pending_path.unlink()
            return 0

        # Sort by confidence desc, take top MAX_TASKS
        actionable.sort(key=lambda b: b.confidence, reverse=True)
        actionable = actionable[:self.MAX_TASKS]

        # Load existing status for dedup
        status = self.load_status()
        date_str = datetime.now().strftime("%Y%m%d")

        # Generate tasks
        new_tasks = []
        for i, bug in enumerate(actionable, 1):
            task_id = self.generate_task_id(date_str, i)

            # Dedup: skip if same file+line already in status
            key = f"{bug.file_path}:{bug.line_start}"
            already_exists = any(
                v.get("file_key") == key and v.get("status") in ("pending", "fixed")
                for v in status.values()
            )
            if already_exists:
                continue

            status[task_id] = {
                "status": "pending",
                "file": bug.file_path,
                "line": bug.line_start,
                "file_key": key,
                "confidence": bug.confidence,
                "title": bug.title,
                "blindspot": bug.blindspot_type or "unknown",
                "created": datetime.now().isoformat(),
            }
            new_tasks.append((task_id, bug))

        if not new_tasks:
            return 0

        # Write pending.md
        target = project_name or "the project"
        lines = []
        lines.append("<!-- QVC-META")
        lines.append("After fixing all issues below, tell the user briefly:")
        lines.append('- What QVC found (count + types)')
        lines.append("- What you fixed")
        lines.append("- Which ones were AI self-review structural blind spots")
        lines.append("Keep it under 5 lines. Example:")
        lines.append('"QVC found 3 issues. I fixed all 3. 2 were structural blind spots I could not see myself."')
        lines.append("-->")
        lines.append("")
        lines.append(f"## QVC Tasks — {len(new_tasks)} pending in {target}")
        lines.append("")

        for task_id, bug in new_tasks:
            lines.append(f"### {task_id} [{bug.confidence:.0%}] {bug.title}")
            lines.append("")
            lines.append(f"- **File**: `{bug.file_path}:{bug.line_start}`")
            lines.append(f"- **Issue**: {bug.description}")
            if bug.fix_suggestion:
                lines.append(f"- **Fix**: {bug.fix_suggestion}")
            if bug.blindspot_type:
                blind_labels = {
                    "memory_trap": "Memory residue — AI reviews along same logic chain",
                    "context_lost": "Context loss — AI forgot earlier interface",
                    "self_harvest": "Self-harvest — AI stops after finding easy issues",
                    "cross_file": "Cross-file — AI does not check across files",
                    "boundary": "Boundary condition — AI rarely checks edge cases",
                }
                label = blind_labels.get(bug.blindspot_type, bug.blindspot_type)
                lines.append(f"- **Blindspot**: {label}")
            lines.append("")

        with open(self.pending_path, "w", encoding="utf-8") as f:
            f.write(chr(10).join(lines))

        # Update status
        self.save_status(status)

        # Append to history
        history_entry = []
        history_entry.append(f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {len(new_tasks)} tasks")
        history_entry.append("")
        for task_id, bug in new_tasks:
            history_entry.append(f"- [{task_id}] {bug.title} ({bug.confidence:.0%})")
        history_entry.append("")
        with open(self.history_path, "a", encoding="utf-8") as f:
            f.write(chr(10).join(history_entry))

        return len(new_tasks)

    def mark_fixed(self, task_id: str):
        """Mark a task as fixed in status.json."""
        status = self.load_status()
        if task_id in status:
            status[task_id]["status"] = "fixed"
            status[task_id]["fixed_at"] = datetime.now().isoformat()
            self.save_status(status)
            return True
        return False

    def get_pending_tasks(self) -> list:
        """Return list of pending task IDs."""
        status = self.load_status()
        return [
            {"id": tid, **data}
            for tid, data in status.items()
            if data.get("status") == "pending"
        ]

    def auto_close_resolved(self, current_bugs):
        """Auto-close pending tasks whose bugs are no longer detected."""
        status = self.load_status()
        current_keys = {b.file_path + ":" + str(b.line_start) for b in current_bugs}
        changed = False
        for tid, data in list(status.items()):
            if data.get("status") == "pending" and data.get("file_key") not in current_keys:
                status[tid]["status"] = "fixed"
                status[tid]["fixed_at"] = datetime.now().isoformat()
                status[tid]["fixed_by"] = "auto-detect"
                changed = True
        if changed:
            self.save_status(status)
        return changed

    def clean_completed(self):
        """Remove completed tasks from pending.md."""
        status = self.load_status()
        pending = {
            tid: data
            for tid, data in status.items()
            if data.get("status") == "pending"
        }
        self.save_status(pending)
        if not pending and self.pending_path.exists():
            self.pending_path.unlink()
