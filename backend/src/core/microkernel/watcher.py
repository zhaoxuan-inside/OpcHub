"""Versioned Hot-Ingestion & File Change Sensing Engine.

Implements the zero-downtime, version-gated hot reloading pattern:
1. Senses file creation, modification, or deletion in monitored directories.
2. Does NOT apply changes immediately to memory; instead marks them as STAGED.
3. Associates detected changes with target API / code versions.
4. Loads code into memory only upon explicit version activation or gateway reload,
   ensuring running transactions and older active versions remain undisturbed.
"""
import ast
import asyncio
from datetime import datetime, timezone
from enum import Enum
import hashlib
import importlib
import importlib.util
import inspect
import logging
import os
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger("opchub.microkernel.watcher")


class FileChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class ChangeStatus(str, Enum):
    DETECTED = "DETECTED"
    STAGED = "STAGED"
    ACTIVATED = "ACTIVATED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content."""
    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def extract_declared_version(code: str) -> Optional[str]:
    """Statically inspect python code via AST to extract declared version metadata.
    
    Checks module-level variables:
      - __version__
      - __operator_version__
      - VERSION
    """
    try:
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ("__version__", "__operator_version__", "VERSION"):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            return node.value.value
    except Exception:
        pass
    return None


class FileChangeRecord(BaseModel):
    file_path: str
    module_name: str
    change_type: FileChangeType
    status: ChangeStatus = ChangeStatus.STAGED
    content_hash: str
    declared_version: Optional[str] = None
    target_version: Optional[str] = None
    detected_at: str = Field(default_factory=utc_now_iso)
    activated_at: Optional[str] = None
    error_message: Optional[str] = None


class VersionedHotReloadEngine:
    """Monitors code changes, isolates them in STAGED status, and loads on version trigger."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        watch_rel_paths: Optional[List[str]] = None,
        poll_interval: float = 3.0,
    ):
        self.base_dir = (base_dir or Path(__file__).resolve().parents[3]).resolve()
        self.watch_rel_paths = watch_rel_paths or ["src/domains", "src/core"]
        self.poll_interval = poll_interval

        # Map of file_path -> (mtime, sha256)
        self._snapshots: Dict[str, Tuple[float, str]] = {}
        # Map of file_path -> FileChangeRecord (currently in STAGED status)
        self._staged_changes: Dict[str, FileChangeRecord] = {}
        # History of activated changes
        self._history: List[FileChangeRecord] = []
        # Background task
        self._bg_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._lock = asyncio.Lock()

        # Initialize baseline snapshot on startup without marking them as changed
        self._build_initial_snapshot()

    def _get_watch_directories(self) -> List[Path]:
        dirs = []
        for p in self.watch_rel_paths:
            full_path = (self.base_dir / p).resolve()
            if full_path.is_dir():
                dirs.append(full_path)
        return dirs

    def _file_to_module_name(self, file_path: Path) -> str:
        """Derive python module import name from file path relative to backend root."""
        try:
            rel = file_path.resolve().relative_to(self.base_dir)
            parts = list(rel.with_suffix("").parts)
            return ".".join(parts)
        except Exception:
            return file_path.stem

    def _build_initial_snapshot(self):
        """Take baseline fingerprint of all existing .py files on startup."""
        for d in self._get_watch_directories():
            for root, _, files in os.walk(d):
                if "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith(".py"):
                        fp = Path(root) / f
                        try:
                            mtime = fp.stat().st_mtime
                            h = compute_file_hash(fp)
                            self._snapshots[str(fp.resolve())] = (mtime, h)
                        except Exception:
                            pass

    def scan_changes(self) -> List[FileChangeRecord]:
        """Scan file system for .py additions, modifications, and deletions.
        
        All detected changes are placed in STAGED status without directly modifying
        the in-memory execution state.
        """
        current_files: Set[str] = set()
        newly_detected: List[FileChangeRecord] = []

        for d in self._get_watch_directories():
            for root, _, files in os.walk(d):
                if "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith(".py"):
                        fp = (Path(root) / f).resolve()
                        str_fp = str(fp)
                        current_files.add(str_fp)

                        try:
                            mtime = fp.stat().st_mtime
                        except OSError:
                            continue

                        # Check if file is new or modified
                        if str_fp not in self._snapshots:
                            content_hash = compute_file_hash(fp)
                            try:
                                code = fp.read_text(encoding="utf-8", errors="replace")
                            except Exception:
                                code = ""
                            declared_ver = extract_declared_version(code)
                            record = FileChangeRecord(
                                file_path=str_fp,
                                module_name=self._file_to_module_name(fp),
                                change_type=FileChangeType.ADDED,
                                status=ChangeStatus.STAGED,
                                content_hash=content_hash,
                                declared_version=declared_ver,
                            )
                            self._staged_changes[str_fp] = record
                            self._snapshots[str_fp] = (mtime, content_hash)
                            newly_detected.append(record)
                            logger.info(f"[HotReload] Detected NEW file (STAGED): {str_fp} (ver={declared_ver or 'auto'})")
                        else:
                            last_mtime, last_hash = self._snapshots[str_fp]
                            if mtime != last_mtime:
                                content_hash = compute_file_hash(fp)
                                if content_hash != last_hash:
                                    try:
                                        code = fp.read_text(encoding="utf-8", errors="replace")
                                    except Exception:
                                        code = ""
                                    declared_ver = extract_declared_version(code)
                                    record = FileChangeRecord(
                                        file_path=str_fp,
                                        module_name=self._file_to_module_name(fp),
                                        change_type=FileChangeType.MODIFIED,
                                        status=ChangeStatus.STAGED,
                                        content_hash=content_hash,
                                        declared_version=declared_ver,
                                    )
                                    self._staged_changes[str_fp] = record
                                    self._snapshots[str_fp] = (mtime, content_hash)
                                    newly_detected.append(record)
                                    logger.info(f"[HotReload] Detected MODIFIED file (STAGED): {str_fp} (ver={declared_ver or 'auto'})")

        # Check for deleted files
        known_files = set(self._snapshots.keys())
        deleted_files = known_files - current_files
        for df in deleted_files:
            record = FileChangeRecord(
                file_path=df,
                module_name=self._file_to_module_name(Path(df)),
                change_type=FileChangeType.DELETED,
                status=ChangeStatus.STAGED,
                content_hash="",
            )
            self._staged_changes[df] = record
            del self._snapshots[df]
            newly_detected.append(record)
            logger.info(f"[HotReload] Detected DELETED file (STAGED): {df}")

        return newly_detected

    def activate_version(
        self,
        target_version: str = "v1.0.0",
        file_paths: Optional[List[str]] = None,
        reload_gateway_routes: bool = True,
    ) -> Dict[str, Any]:
        """Atomically load staged python changes into memory for the target version.
        
        Steps:
        1. Pre-validates python syntax via AST; fails safely if syntax is invalid.
        2. Unloads old module reference from sys.modules and re-imports freshly.
        3. Synchronizes with gateway scenario router and microkernel atomic registry.
        4. Transitions record status from STAGED to ACTIVATED.
        """
        self.scan_changes()

        if file_paths:
            targets = [self._staged_changes[fp] for fp in file_paths if fp in self._staged_changes]
        else:
            # All staged changes matching declared_version, or those with None (defaults to target_version)
            targets = [
                rec for rec in self._staged_changes.values()
                if rec.declared_version is None or rec.declared_version == target_version
            ]

        activated: List[str] = []
        failed: List[Dict[str, str]] = []

        for rec in targets:
            fp = Path(rec.file_path)
            mod_name = rec.module_name

            if rec.change_type == FileChangeType.DELETED:
                # Remove from sys.modules if present
                sys.modules.pop(mod_name, None)
                rec.status = ChangeStatus.ACTIVATED
                rec.target_version = target_version
                rec.activated_at = utc_now_iso()
                activated.append(mod_name)
                self._staged_changes.pop(rec.file_path, None)
                self._history.append(rec)
                continue

            # 1. AST Syntax validation
            try:
                code_bytes = fp.read_bytes()
                ast.parse(code_bytes, filename=str(fp))
            except Exception as e:
                rec.status = ChangeStatus.FAILED
                rec.error_message = f"Syntax error: {str(e)}"
                failed.append({"file": rec.file_path, "module": mod_name, "error": rec.error_message})
                logger.error(f"[HotReload] Activation rejected for {rec.file_path}: {e}")
                continue

            # 2. Invalidate import cache and safely re-import
            try:
                importlib.invalidate_caches()
                if mod_name in sys.modules:
                    # Clean reload
                    old_mod = sys.modules[mod_name]
                    try:
                        new_mod = importlib.reload(old_mod)
                    except Exception:
                        # Fallback to pop and re-import
                        sys.modules.pop(mod_name, None)
                        new_mod = importlib.import_module(mod_name)
                else:
                    new_mod = importlib.import_module(mod_name)

                rec.status = ChangeStatus.ACTIVATED
                rec.target_version = target_version
                rec.activated_at = utc_now_iso()
                rec.error_message = None
                activated.append(mod_name)
                self._staged_changes.pop(rec.file_path, None)
                self._history.append(rec)
                logger.info(f"[HotReload] Successfully ACTIVATED module in memory: '{mod_name}' (ver={target_version})")
            except Exception as e:
                rec.status = ChangeStatus.FAILED
                rec.error_message = f"Module import error: {str(e)}"
                failed.append({"file": rec.file_path, "module": mod_name, "error": str(e)})
                logger.error(f"[HotReload] Import failed for {mod_name}: {e}")

        # 3. Synchronize with gateway routes if requested
        gateway_reloaded = False
        gateway_routes_count = 0
        if reload_gateway_routes:
            try:
                from src.core.gateway.config_loader import load_scenario_routes_from_yaml
                from src.core.gateway.router import scenario_router
                gateway_routes_count = load_scenario_routes_from_yaml(scenario_router)
                gateway_reloaded = True
            except Exception as e:
                logger.error(f"[HotReload] Gateway routes sync failed during activation: {e}")

        return {
            "status": "SUCCESS" if not failed else "PARTIAL",
            "activated_version": target_version,
            "activated_count": len(activated),
            "activated_modules": activated,
            "failed_count": len(failed),
            "failed_items": failed,
            "gateway_reloaded": gateway_reloaded,
            "gateway_routes_count": gateway_routes_count,
            "timestamp": utc_now_iso(),
        }

    def rollback_staged(self, file_path: Optional[str] = None):
        """Discard staged changes without loading them into memory."""
        if file_path:
            if file_path in self._staged_changes:
                rec = self._staged_changes.pop(file_path)
                rec.status = ChangeStatus.ROLLED_BACK
                self._history.append(rec)
        else:
            for fp, rec in list(self._staged_changes.items()):
                rec.status = ChangeStatus.ROLLED_BACK
                self._history.append(rec)
            self._staged_changes.clear()

    async def _watch_loop(self):
        """Asynchronous background loop that continuously senses file changes."""
        logger.info(f"[HotReload] File sensing watcher loop started (poll_interval={self.poll_interval}s)")
        while self._is_running:
            try:
                self.scan_changes()
            except Exception as e:
                logger.warning(f"[HotReload] Watcher cycle exception: {e}")
            await asyncio.sleep(self.poll_interval)

    def start_background_watcher(self):
        """Start non-blocking file sensory watcher in background."""
        if self._is_running:
            return
        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
            self._bg_task = loop.create_task(self._watch_loop())
        except RuntimeError:
            pass

    def stop_background_watcher(self):
        """Stop background watcher loop."""
        self._is_running = False
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            self._bg_task = None
        logger.info("[HotReload] File sensing watcher loop stopped")

    def get_status(self) -> Dict[str, Any]:
        """Introspection payload for monitoring and governance."""
        return {
            "is_watcher_running": self._is_running,
            "poll_interval_seconds": self.poll_interval,
            "watch_directories": [str(d) for d in self._get_watch_directories()],
            "monitored_files_count": len(self._snapshots),
            "staged_changes_count": len(self._staged_changes),
            "staged_changes": [rec.model_dump() for rec in self._staged_changes.values()],
            "recent_activations": [rec.model_dump() for rec in self._history[-10:]],
        }


# Singleton engine instance
hot_reload_engine = VersionedHotReloadEngine()
