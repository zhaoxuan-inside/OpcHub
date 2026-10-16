"""Tests for AST Security Scanner."""
from src.core.microkernel.sandbox import validate_python_code


def test_valid_python_code():
    valid_code = """
def calculate_vat_exemption(quarterly_revenue: float) -> dict:
    is_exempt = quarterly_revenue <= 300000.0
    return {
        "exempt": is_exempt,
        "tax_due": 0.0 if is_exempt else quarterly_revenue * 0.01
    }
"""
    result = validate_python_code(valid_code)
    assert result.is_safe is True
    assert len(result.violations) == 0
    assert "calculate_vat_exemption" in result.parsed_functions
    assert result.signature_hash is not None


def test_forbidden_os_import():
    malicious_code = """
import os

def exploit():
    os.system("rm -rf /")
"""
    result = validate_python_code(malicious_code)
    assert result.is_safe is False
    assert any("import 'os'" in v for v in result.violations)


def test_forbidden_subprocess_import_from():
    malicious_code = """
from subprocess import Popen

def run_cmd():
    Popen(["ls", "-la"])
"""
    result = validate_python_code(malicious_code)
    assert result.is_safe is False
    assert any("subprocess" in v for v in result.violations)


def test_forbidden_eval_call():
    malicious_code = """
def dangerous(payload: str):
    return eval(payload)
"""
    result = validate_python_code(malicious_code)
    assert result.is_safe is False
    assert any("eval()" in v for v in result.violations)


def test_syntax_error_handled_cleanly():
    broken_code = "def syntax_err(: broken"
    result = validate_python_code(broken_code)
    assert result.is_safe is False
    assert any("Syntax Error" in v for v in result.violations)
