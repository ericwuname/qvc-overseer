"""进化引擎 - 基因池同步器"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from .fingerprint import Fingerprint
from .fingerprint_store import FingerprintStore


class GenePoolSyncer:
    """同步本地指纹库与远程基因池"""

    # Default gene pool (GitHub). Use Gitee mirror for China: https://gitee.com/qvc-project/fingerprints.git
    DEFAULT_POOL_URL = "https://github.com/ericwuname/qvc-overseer.git  # TODO: create separate fingerprints repo"

    def __init__(self, store: FingerprintStore, pool_url: str | None = None):
        self.store = store
        self.pool_url = pool_url or self.DEFAULT_POOL_URL
        self.pool_dir = Path.home() / ".qvc" / "gene_pool"

    def sync(self) -> dict:
        """从基因池同步最新指纹"""
        result = {
            "success": False,
            "new_fingerprints": 0,
            "updated_fingerprints": 0,
            "message": "",
            "pool_stats": {},
        }

        # 1. Clone或Pull基因池
        if not self._update_pool():
            result["message"] = "基因池同步失败：无法连接远程仓库。离线模式继续。"
            return result

        # 2. 扫描基因池中的指纹文件
        pool_fingerprints = self._load_pool_fingerprints()

        # 3. 导入新指纹
        new_count = 0
        for fp_data in pool_fingerprints:
            try:
                fp = Fingerprint.from_dict(fp_data)
                existing = self.store.get_fingerprint(fp.id)
                if existing is None:
                    self.store.import_from_pool([fp])
                    new_count += 1
                elif existing.occurrence_count < fp.occurrence_count:
                    # 更新出现次数
                    self.store.add_fingerprint(fp, source="pool")
                    result["updated_fingerprints"] += 1
            except Exception:
                continue

        result["success"] = True
        result["new_fingerprints"] = new_count
        result["message"] = f"同步完成：新增 {new_count} 条指纹，更新 {result['updated_fingerprints']} 条"
        result["pool_stats"] = {
            "total_in_pool": len(pool_fingerprints),
            "pool_updated_at": self._get_pool_updated_at(),
        }

        # 记录同步事件
        self.store.log_event("pool_sync", result["message"])

        return result

    def check_updates(self) -> dict:
        """检查基因池是否有更新"""
        if not self.pool_dir.exists():
            return {"has_updates": True, "message": "基因池尚未初始化"}

        try:
            result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(self.pool_dir),
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"has_updates": False, "message": "无法检查更新"}

            # Detect default branch (main or master, GitHub/Gitee compatible)
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.pool_dir), capture_output=True, text=True, timeout=10
            )
            default_branch = branch_result.stdout.strip() or "main"
            result = subprocess.run(
                ["git", "rev-list", f"HEAD..origin/{default_branch}", "--count"],
                cwd=str(self.pool_dir),
                capture_output=True, text=True, timeout=10
            )
            count = int(result.stdout.strip() or "0")
            return {
                "has_updates": count > 0,
                "commits_behind": count,
                "message": f"基因池有 {count} 个新提交" if count > 0 else "基因池已是最新",
            }
        except Exception:
            return {"has_updates": False, "message": "离线模式"}

    def _update_pool(self) -> bool:
        """Update local gene pool. Git-first, graceful fallback to local files."""
        has_local = self.pool_dir.exists() and (self.pool_dir / "fingerprints").exists()
        
        try:
            self.pool_dir.mkdir(parents=True, exist_ok=True)
            is_git_repo = (self.pool_dir / ".git").exists()
            
            if is_git_repo:
                result = subprocess.run(
                    ["git", "pull", "--depth", "1"],
                    cwd=str(self.pool_dir),
                    capture_output=True, text=True, timeout=60
                )
            else:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", self.pool_url, str(self.pool_dir)],
                    capture_output=True, text=True, timeout=60
                )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        
        # Git failed: use local gene pool if available
        if has_local:
            return True
        
        # Try to link local pool from home dir
        local_src = Path.home() / ".qvc" / "gene_pool" / "fingerprints"
        if local_src.exists() and local_src != (self.pool_dir / "fingerprints"):
            import shutil
            shutil.copytree(str(local_src), str(self.pool_dir / "fingerprints"), dirs_exist_ok=True)
            return True
        
        return False

    def _load_pool_fingerprints(self) -> list[dict]:
        """加载基因池中的所有指纹"""
        fingerprints = []
        fp_dir = self.pool_dir / "fingerprints"
        if not fp_dir.exists():
            return fingerprints

        for json_file in fp_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        fingerprints.extend(data)
                    elif isinstance(data, dict) and "fingerprints" in data:
                        fingerprints.extend(data["fingerprints"])
                    elif isinstance(data, dict) and "fingerprint_id" in data:
                        fingerprints.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        return fingerprints

    def _get_pool_updated_at(self) -> str:
        """获取基因池最后更新时间"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=str(self.pool_dir),
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
