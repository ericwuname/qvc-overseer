"""进化引擎 - 贡献器：生成匿名化指纹供社区贡献"""

import json
from pathlib import Path
from datetime import datetime
from .fingerprint_store import FingerprintStore
from .fingerprint import Fingerprint, FingerprintStatus


class Contributor:
    """管理指纹贡献流程"""

    def __init__(self, store: FingerprintStore, pool_dir: Path | None = None):
        self.store = store
        self.pool_dir = pool_dir or Path.home() / ".qvc" / "pool"
        self.pool_dir.mkdir(parents=True, exist_ok=True)

    def preview_contributable(self) -> list[dict]:
        """预览可贡献的指纹"""
        # 获取本地激活的指纹，且尚未贡献的
        conn = __import__('sqlite3').connect(str(self.store.db_path))
        try:
            rows = conn.execute(
                "SELECT id, pattern_name, category, occurrence_count, confidence "
                "FROM fingerprints WHERE status = 'active' AND source = 'local'"
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "category": r[2],
                    "occurrences": r[3],
                    "confidence": r[4],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def generate_contribution(self, fingerprint_ids: list[str]) -> list[dict]:
        """为指定指纹生成匿名化的贡献数据"""
        contributions = []
        for fp_id in fingerprint_ids:
            fp = self.store.get_fingerprint(fp_id)
            if fp and fp.status == FingerprintStatus.ACTIVE:
                # 完全匿名化：移除所有可追溯信息
                anon = fp.to_dict()
                anon["contributor"] = "anonymous"
                anon["source_bugs"] = []  # 不暴露原始缺陷
                contributions.append(anon)
        return contributions

    def save_contribution_file(self, contributions: list[dict]) -> Path:
        """将贡献保存为JSON文件，准备提交到基因池"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contribution_{timestamp}.json"
        filepath = self.pool_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "contributor": "anonymous",
                "fingerprints": contributions,
            }, f, ensure_ascii=False, indent=2)

        return filepath

    def submit_via_pr(self, contributions: list[dict], repo_url: str) -> dict:
        """通过PR提交流程（需git支持）"""
        import subprocess
        import tempfile

        if not contributions:
            return {"success": False, "message": "没有可贡献的指纹"}

        # 1. 保存贡献文件
        contrib_file = self.save_contribution_file(contributions)

        # 2. 提示用户手动提PR
        return {
            "success": True,
            "message": "指纹已准备就绪，请手动提交Pull Request",
            "contribution_file": str(contrib_file),
            "fingerprint_count": len(contributions),
            "instructions": [
                f"1. Fork 基因池仓库: {repo_url}",
                f"2. 将 {contrib_file.name} 放入 fingerprints/ 目录",
                "3. 提交PR，标题: feat: add {n} fingerprints from community".format(n=len(contributions)),
                "4. 等待社区审核",
            ],
        }
