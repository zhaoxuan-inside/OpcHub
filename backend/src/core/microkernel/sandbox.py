"""AST Security Scanner & Restricted-Namespace Loader for Hot-Loaded Python Operators.

Implements the four-firewall design for microkernel operators:

1. AST static lexical/syntax sandbox scan (forbidden modules / calls / attribute escapes)
2. Entry-point signature convention verification (must export an async entry function)
3. Restricted isolated execution namespace compilation & loading (builtins stripped)
4. Register into ActionRegistry + tamper-evident audit log (performed by caller)
"""
import ast
import hashlib
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("opchub.microkernel.sandbox")


# ---------------------------------------------------------------------------
# Firewall 1: forbidden modules / calls / attribute escapes
# ---------------------------------------------------------------------------
FORBIDDEN_MODULES = {
    # destructive low-level system libraries
    "os", "sys", "subprocess", "shutil", "socket", "pty", "commands",
    "posix", "nt", "builtins", "__builtin__", "importlib", "pickle", "shelve",
    # code generation / reflection escape hatches
    "ctypes", "marshal", "mmap", "fcntl", "resource", "signal", "gc",
    "inspect", "types", "code", "codeop", "zipimport", "runpy", "pkgutil",
    "site", "atexit", "multiprocessing", "threading", "asyncio",
    # filesystem / IO / network
    "pathlib", "io", "tempfile", "glob", "sqlite3", "http", "urllib",
    "requests", "httpx", "ftplib", "smtplib", "telnetlib", "xmlrpc",
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "memoryview", "exit", "quit", "help", "dir", "super",
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__class__", "__bases__", "__base__", "__mro__",
    "__globals__", "__builtins__", "__dict__", "__getattribute__", "__setattr__",
    "__delattr__", "__code__", "__closure__", "__reduce__", "__reduce_ex__",
    "__init_subclass__", "__subclasshook__", "__loader__", "__spec__", "__import__",
}

# Builtins whitelist injected into the restricted execution namespace (no I/O, no reflection).
SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "divmod": divmod,
    "enumerate": enumerate, "filter": filter, "float": float, "format": format,
    "frozenset": frozenset, "hash": hash, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "len": len, "list": list, "map": map, "max": max,
    "min": min, "pow": pow, "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str,
    "sum": sum, "tuple": tuple, "zip": zip, "True": True, "False": False, "None": None,
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "RuntimeError": RuntimeError, "ArithmeticError": ArithmeticError,
    "ZeroDivisionError": ZeroDivisionError, "IndexError": IndexError,
    "AttributeError": AttributeError, "PermissionError": PermissionError,
    "StopIteration": StopIteration, "NotImplementedError": NotImplementedError,
}


@dataclass
class SandboxValidationResult:
    is_safe: bool
    violations: list[str] = field(default_factory=list)
    parsed_functions: list[str] = field(default_factory=list)
    async_functions: list[str] = field(default_factory=list)
    signature_hash: Optional[str] = None


class ASTSecurityScanner(ast.NodeVisitor):
    """Inspects AST nodes to disallow hazardous syscalls, imports and reflection escapes."""

    def __init__(self):
        self.violations: list[str] = []
        self.functions: list[str] = []
        self.async_functions: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden import '{alias.name}' detected at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden import-from '{node.module}' detected at line {node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(
                    f"Forbidden dangerous function call '{node.func.id}()' detected at line {node.lineno}"
                )
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in {"system", "popen", "spawn", "execv", "execve"}:
                self.violations.append(
                    f"Forbidden attribute call '.{node.func.attr}()' detected at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(
                f"Forbidden reflection attribute '.{node.attr}' detected at line {node.lineno}"
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(node.name)
        self.async_functions.append(node.name)
        self.generic_visit(node)


def validate_python_code(code: str) -> SandboxValidationResult:
    """Validate a Python script string for security compliance (Firewall 1)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return SandboxValidationResult(
            is_safe=False,
            violations=[f"Python Syntax Error at line {e.lineno}: {e.msg}"],
        )

    scanner = ASTSecurityScanner()
    scanner.visit(tree)

    is_safe = len(scanner.violations) == 0
    sig = None
    if is_safe:
        sig = "sig_sha256_" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    return SandboxValidationResult(
        is_safe=is_safe,
        violations=scanner.violations,
        parsed_functions=scanner.functions,
        async_functions=scanner.async_functions,
        signature_hash=sig,
    )


# ---------------------------------------------------------------------------
# Firewall 2 + 3: entry-point convention verification & restricted loading
# ---------------------------------------------------------------------------
DEFAULT_ENTRY_FUNCTION = "action_entry"


@dataclass
class LoadedOperator:
    """A validated, restricted-namespace-loaded dynamic operator ready for registration."""
    name: str
    entry_function: str
    handler: Callable[[dict, dict], Any]
    signature_hash: str
    source_bytes: int


def _adapt_entry(entry: Callable) -> Callable:
    """Adapt a script entry function to the runtime operator signature (inputs, context) -> awaitable dict."""
    try:
        params = [
            p for p in inspect.signature(entry).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
    except (TypeError, ValueError):
        params = []
    arg_count = len(params)

    async def _invoke(inputs: dict, context: dict) -> dict:
        if arg_count == 0:
            res = entry()
        elif arg_count == 1:
            res = entry(inputs)
        else:
            res = entry(inputs, context)
        if inspect.isawaitable(res):
            res = await res
        if res is None:
            return {}
        if not isinstance(res, dict):
            return {"result": res}
        return res

    return _invoke


def load_operator_from_source(code: str, entry_function: Optional[str] = None) -> LoadedOperator:
    """Validate, compile and load a dynamic operator script in a restricted namespace.

    Enforces Firewall 1 (AST scan), Firewall 2 (async entry-point convention) and
    Firewall 3 (restricted namespace execution with builtins stripped to a whitelist).
    """
    # Firewall 1: static AST security scan
    validation = validate_python_code(code)
    if not validation.is_safe:
        raise ValueError("Script rejected by sandbox scanner: " + "; ".join(validation.violations))

    # Firewall 2: entry-point convention verification (must export an async function)
    if entry_function:
        if entry_function not in validation.parsed_functions:
            raise ValueError(
                f"Declared entry function '{entry_function}' not found in script. "
                f"Available functions: {validation.parsed_functions}"
            )
        resolved_entry = entry_function
    elif DEFAULT_ENTRY_FUNCTION in validation.async_functions:
        resolved_entry = DEFAULT_ENTRY_FUNCTION
    elif validation.async_functions:
        resolved_entry = validation.async_functions[0]
    else:
        raise ValueError(
            "Entry-point convention violated: script must define at least one "
            "`async def` function (recommended name: action_entry)"
        )

    if resolved_entry not in validation.async_functions:
        raise ValueError(
            f"Entry-point convention violated: entry '{resolved_entry}' must be declared `async def`"
        )

    # Firewall 3: restricted isolated namespace compilation & loading
    namespace: dict[str, Any] = {
        "__name__": "opchub_dynamic_operator",
        "__builtins__": dict(SAFE_BUILTINS),
    }
    try:
        compiled = compile(code, "<dynamic_operator>", "exec")
        exec(compiled, namespace)  # noqa: S102 - sandboxed: AST-scanned + builtins whitelist
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Script execution during load failed: {exc}") from exc

    entry = namespace.get(resolved_entry)
    if entry is None or not callable(entry) or not inspect.iscoroutinefunction(entry):
        raise ValueError(
            f"Entry-point convention violated: '{resolved_entry}' must be an async callable"
        )

    return LoadedOperator(
        name="",
        entry_function=resolved_entry,
        handler=_adapt_entry(entry),
        signature_hash=validation.signature_hash or "",
        source_bytes=len(code.encode("utf-8")),
    )
