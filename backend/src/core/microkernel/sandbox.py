"""AST Static Security Scanner for Hot-Loaded Python Operators."""
import ast
from dataclasses import dataclass, field


FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "pty", "commands",
    "posix", "nt", "builtins", "__builtin__", "importlib", "pickle", "shelve"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input"
}


@dataclass
class SandboxValidationResult:
    is_safe: bool
    violations: list[str] = field(default_factory=list)
    parsed_functions: list[str] = field(default_factory=list)
    signature_hash: str | None = None


class ASTSecurityScanner(ast.NodeVisitor):
    """Inspects AST nodes to disallow hazardous syscalls and imports."""

    def __init__(self):
        self.violations: list[str] = []
        self.functions: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(
                    f"Forbidden import '{alias.name}' detected at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(
                    f"Forbidden import-from '{node.module}' detected at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(
                    f"Forbidden dangerous function call '{node.func.id}()' detected at line {node.lineno}"
                )
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in {"system", "popen", "spawn", "execv"}:
                self.violations.append(
                    f"Forbidden attribute call '.{node.func.attr}()' detected at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)


def validate_python_code(code: str) -> SandboxValidationResult:
    """Validate a Python script string for security compliance."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return SandboxValidationResult(
            is_safe=False,
            violations=[f"Python Syntax Error at line {e.lineno}: {e.msg}"]
        )

    scanner = ASTSecurityScanner()
    scanner.visit(tree)

    is_safe = len(scanner.violations) == 0
    sig = None
    if is_safe:
        import hashlib
        sig = "sig_sha256_" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    return SandboxValidationResult(
        is_safe=is_safe,
        violations=scanner.violations,
        parsed_functions=scanner.functions,
        signature_hash=sig
    )
