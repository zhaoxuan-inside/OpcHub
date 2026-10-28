"""Verification Suite for Versioned Hot-Ingestion & Live Reloading Engine."""
import os
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.microkernel.watcher import (
    hot_reload_engine,
    FileChangeType,
    ChangeStatus,
    extract_declared_version,
)

client = TestClient(app)


def test_engine_initialization_and_status():
    """Verify engine baseline snapshotting and status payload."""
    status = hot_reload_engine.get_status()
    assert "watch_directories" in status
    assert status["monitored_files_count"] > 0
    assert isinstance(status["staged_changes"], list)


def test_declared_version_ast_extraction():
    """Verify AST statically extracts __version__ or __operator_version__ without executing code."""
    code_sample = '''
__version__ = "v2.1.0"
def run():
    return 42
'''
    assert extract_declared_version(code_sample) == "v2.1.0"

    code_op = '''
__operator_version__ = "v1.3.4"
'''
    assert extract_declared_version(code_op) == "v1.3.4"

    code_empty = 'x = 10'
    assert extract_declared_version(code_empty) is None


def test_file_addition_staging_and_versioned_activation():
    """Verify that added file is staged, not directly executed, and activates only on target version."""
    temp_dir = Path(__file__).resolve().parents[1] / "src" / "domains" / "_dynamic_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / "hot_op_v1.py"

    try:
        # 1. Create a new python file
        temp_file.write_text(
            '__version__ = "v1.5.0"\n'
            'def get_indicator():\n'
            '    return "INITIAL_V1"\n',
            encoding="utf-8"
        )

        # 2. Scan changes: file must be detected and STAGED, NOT yet imported
        changes = hot_reload_engine.scan_changes()
        staged_fps = [c.file_path for c in changes]
        assert str(temp_file.resolve()) in staged_fps

        rec = hot_reload_engine._staged_changes[str(temp_file.resolve())]
        assert rec.status == ChangeStatus.STAGED
        assert rec.declared_version == "v1.5.0"
        mod_name = rec.module_name

        # Verify not yet loaded into memory
        assert mod_name not in sys.modules

        # 3. Activate a DIFFERENT version (e.g. v1.0.0) -> v1.5.0 should NOT activate
        diff_res = hot_reload_engine.activate_version("v1.0.0")
        assert mod_name not in diff_res.get("activated_modules", [])
        assert str(temp_file.resolve()) in hot_reload_engine._staged_changes

        # 4. Activate MATCHING version (v1.5.0) -> formally loads into memory
        match_res = hot_reload_engine.activate_version("v1.5.0")
        assert mod_name in match_res.get("activated_modules", [])
        assert mod_name in sys.modules

        loaded_mod = sys.modules[mod_name]
        assert loaded_mod.get_indicator() == "INITIAL_V1"

        # 5. Modify the file
        temp_file.write_text(
            '__version__ = "v1.5.0"\n'
            'def get_indicator():\n'
            '    return "UPDATED_V2"\n',
            encoding="utf-8"
        )
        mod_changes = hot_reload_engine.scan_changes()
        assert str(temp_file.resolve()) in [c.file_path for c in mod_changes]

        # Prior to activation, memory STILL returns the old value (no uncoordinated mutation)
        assert sys.modules[mod_name].get_indicator() == "INITIAL_V1"

        # 6. Activate again -> updates memory
        update_res = hot_reload_engine.activate_version("v1.5.0")
        assert mod_name in update_res.get("activated_modules", [])
        assert sys.modules[mod_name].get_indicator() == "UPDATED_V2"

    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
        hot_reload_engine.scan_changes()
        hot_reload_engine.activate_version("v1.5.0")
        if temp_dir.exists():
            try:
                temp_dir.rmdir()
            except OSError:
                pass


def test_syntax_error_quarantine_safety():
    """Verify that files with syntax errors are quarantined and do not crash the engine."""
    temp_dir = Path(__file__).resolve().parents[1] / "src" / "domains" / "_dynamic_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    bad_file = temp_dir / "bad_syntax.py"

    try:
        bad_file.write_text("def broken_syntax(::: invalid", encoding="utf-8")
        hot_reload_engine.scan_changes()

        res = hot_reload_engine.activate_version("v1.0.0", file_paths=[str(bad_file.resolve())])
        assert res["failed_count"] == 1
        assert "Syntax error" in res["failed_items"][0]["error"]
    finally:
        if bad_file.exists():
            bad_file.unlink()
        hot_reload_engine.scan_changes()
        if temp_dir.exists():
            try:
                temp_dir.rmdir()
            except OSError:
                pass


def test_single_gateway_endpoint_routed_by_request_body():
    """Verify that all framework governance and hot-reload operations dispatch through the SINGLE gateway endpoint.
    
    The entire system only has ONE entrypoint: POST /api/welcom/opc_world.
    All routing decisions are made by 'scenario' and 'version' in the request body.
    """
    # 1. framework.hot-reload.status via request body scenario
    r_stat = client.post("/api/welcom/opc_world", json={
        "scenario": "framework.hot-reload.status",
        "version": "v1.0.0",
        "payload": {},
    })
    assert r_stat.status_code == 200
    res_data = r_stat.json()
    assert res_data["code"] == 200
    assert "monitored_files_count" in res_data["data"]
    assert res_data["data"]["monitored_files_count"] > 0

    # 2. framework.hot-reload.scan via request body scenario
    r_scan = client.post("/api/welcom/opc_world", json={
        "scenario": "framework.hot-reload.scan",
        "version": "v1.0.0",
        "payload": {},
    })
    assert r_scan.status_code == 200
    scan_data = r_scan.json()
    assert scan_data["code"] == 200
    assert scan_data["data"]["status"] == "ok"

    # 3. framework.hot-reload.activate via request body scenario
    r_act = client.post("/api/welcom/opc_world", json={
        "scenario": "framework.hot-reload.activate",
        "version": "v1.0.0",
        "payload": {"version": "v1.0.0"},
    })
    assert r_act.status_code == 200
    act_data = r_act.json()
    assert act_data["code"] == 200
    assert act_data["data"]["activated_version"] == "v1.0.0"

    # 4. framework.gateway.reload via request body scenario
    r_reload = client.post("/api/welcom/opc_world", json={
        "scenario": "framework.gateway.reload",
        "version": "v1.0.0",
        "payload": {},
    })
    assert r_reload.status_code == 200
    reload_data = r_reload.json()
    assert reload_data["code"] == 200
    assert "hot_reload" in reload_data["data"]

    # 5. gateway.rules via request body scenario
    r_rules = client.post("/api/welcom/opc_world", json={
        "scenario": "gateway.rules",
        "version": "v1.0.0",
        "payload": {},
    })
    assert r_rules.status_code == 200
    rules_data = r_rules.json()
    assert rules_data["code"] == 200
    assert isinstance(rules_data["data"], list)
    assert len(rules_data["data"]) >= 50

