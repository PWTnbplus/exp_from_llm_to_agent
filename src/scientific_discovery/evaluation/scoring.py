"""Deterministic structural and mechanistic scoring for submitted laws.

The scorer runs only after submission, inside the evaluator boundary.  It does
not expose the target function or the OOD interventions to either runner.
"""

from __future__ import annotations

import ast
import inspect
import math
import textwrap
from typing import Any, Mapping


# This object is the code-level copy of the preregistered protocol in
# ``configs/evaluation.json``.  Formal runs must use these values unchanged.
SCORING_PROTOCOL: dict[str, Any] = {
    "version": "scoring-v1",
    "validation_points": 128,
    "ood_points": 64,
    "relative_rmse_threshold": 1e-5,
    "ood_relative_rmse_threshold": 1e-5,
    "minimum_valid_ood_points": 16,
    "structural_recovery_required": True,
}


def scoring_protocol() -> dict[str, Any]:
    """Return a defensive copy of the locked scoring parameters."""

    return dict(SCORING_PROTOCOL)


def _function_node(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(textwrap.dedent(source), mode="exec")
    functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(functions) != 1 or isinstance(functions[0], ast.AsyncFunctionDef):
        raise ValueError("law source must contain exactly one synchronous function")
    return functions[0]


def _numeric_global(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


class _Canonicalizer:
    """Small, deterministic expression normalizer.

    It deliberately handles only expression forms used by the pinned direct
    NewtonBench laws.  Unknown constructs are rejected instead of being
    treated as equivalent by a permissive string comparison.
    """

    def __init__(self, globals_: Mapping[str, Any], parameters: set[str]):
        self.globals = globals_
        self.parameters = parameters

    def expression(self, node: ast.AST, locals_: Mapping[str, tuple]) -> tuple:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return ("bool", node.value)
            if isinstance(node.value, (int, float)):
                value = float(node.value)
                if not math.isfinite(value):
                    raise ValueError("non-finite literal")
                return ("const", value)
            if isinstance(node.value, str):
                return ("str", node.value)
            raise ValueError("unsupported literal")

        if isinstance(node, ast.Name):
            if node.id in locals_:
                return locals_[node.id]
            value = _numeric_global(self.globals.get(node.id))
            if value is not None:
                return ("const", value)
            if node.id in self.parameters:
                return ("var", node.id)
            return ("name", node.id)

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in {"math", "np", "numpy"}:
                if node.attr == "e":
                    return ("const", math.e)
                if node.attr == "pi":
                    return ("const", math.pi)
                return ("function", node.attr)
            raise ValueError("unsupported attribute access")

        if isinstance(node, ast.UnaryOp):
            value = self.expression(node.operand, locals_)
            if isinstance(node.op, ast.USub):
                if value[0] == "const":
                    return ("const", -value[1])
                return ("neg", value)
            if isinstance(node.op, ast.UAdd):
                return value
            raise ValueError("unsupported unary operator")

        if isinstance(node, ast.BinOp):
            left = self.expression(node.left, locals_)
            right = self.expression(node.right, locals_)
            if isinstance(node.op, ast.Add):
                return self._commutative("add", (left, right))
            if isinstance(node.op, ast.Sub):
                return self._commutative("add", (left, ("neg", right)))
            if isinstance(node.op, ast.Mult):
                return self._commutative("mul", (left, right))
            if isinstance(node.op, ast.Div):
                return self._commutative("mul", (left, ("pow", right, ("const", -1.0))))
            if isinstance(node.op, ast.Pow):
                return ("pow", left, right)
            raise ValueError("unsupported binary operator")

        if isinstance(node, ast.Call):
            name = self._call_name(node.func)
            if name == "float" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "nan":
                return ("nan",)
            args = tuple(self.expression(arg, locals_) for arg in node.args)
            if name == "float" and len(args) == 1:
                return args[0]
            if name == "pow" and len(args) == 2:
                return ("pow", args[0], args[1])
            if name == "sqrt" and len(args) == 1:
                return ("pow", args[0], ("const", 0.5))
            keywords = tuple(
                (keyword.arg, self.expression(keyword.value, locals_))
                for keyword in node.keywords
            )
            return ("call", name, args, keywords)

        if isinstance(node, ast.IfExp):
            return (
                "if",
                self.expression(node.test, locals_),
                self.expression(node.body, locals_),
                self.expression(node.orelse, locals_),
            )

        if isinstance(node, ast.Compare):
            left = self.expression(node.left, locals_)
            comparisons = tuple(
                (type(op).__name__, self.expression(comparator, locals_))
                for op, comparator in zip(node.ops, node.comparators)
            )
            return ("compare", left, comparisons)

        raise ValueError(f"unsupported expression node: {type(node).__name__}")

    @staticmethod
    def _call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in {"math", "np", "numpy"}:
                return node.attr
        raise ValueError("unsupported callable")

    def _commutative(self, operator: str, terms: tuple[tuple, ...]) -> tuple:
        flattened: list[tuple] = []
        for term in terms:
            if term[0] == operator:
                flattened.extend(term[1])
            else:
                flattened.append(term)
        # Simplify only identities that preserve the declared algebraic
        # equivalence class.  This accepts harmless parentheses and x + 0,
        # while retaining nontrivial structure for adversarial candidates.
        if operator == "add":
            flattened = [term for term in flattened if term != ("const", 0.0)]
            if not flattened:
                return ("const", 0.0)
            if len(flattened) == 1:
                return flattened[0]
        if operator == "mul":
            if ("const", 0.0) in flattened:
                return ("const", 0.0)
            flattened = [term for term in flattened if term != ("const", 1.0)]
            if not flattened:
                return ("const", 1.0)
            if len(flattened) == 1:
                return flattened[0]
        return (operator, tuple(sorted(flattened, key=repr)))


def _assignment_bindings(function: ast.FunctionDef, normalizer: _Canonicalizer) -> dict[str, tuple]:
    bindings: dict[str, tuple] = {}

    def bind(target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, ast.Name):
            bindings[target.id] = normalizer.expression(value, bindings)
            return
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
            for target_item, value_item in zip(target.elts, value.elts):
                bind(target_item, value_item)

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                bind(target, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            bind(node.target, node.value)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in function.body:
        visit(statement)
    return bindings


def _is_trivial_return(expression: tuple) -> bool:
    return expression == ("nan",) or expression == ("const", 0.0)


def canonical_law_expression(source: str, globals_: Mapping[str, Any] | None = None, parameters: list[str] | None = None) -> tuple:
    """Return a canonical AST fingerprint for the main law expression."""

    function = _function_node(source)
    normalizer = _Canonicalizer(globals_ or {}, set(parameters or [arg.arg for arg in function.args.args]))
    bindings = _assignment_bindings(function, normalizer)
    candidates = []
    for node in ast.walk(function):
        if isinstance(node, ast.Return) and node.value is not None:
            expression = normalizer.expression(node.value, bindings)
            if not _is_trivial_return(expression):
                candidates.append(expression)
    if not candidates:
        returns = [
            normalizer.expression(node.value, bindings)
            for node in ast.walk(function)
            if isinstance(node, ast.Return) and node.value is not None
        ]
        if not returns:
            raise ValueError("law function has no return expression")
        candidates = returns
    return max(candidates, key=lambda value: len(repr(value)))


def structurally_equivalent(candidate_source: str, target_function: Any, parameters: list[str]) -> bool:
    """Compare executable candidate and target expressions by canonical AST."""

    try:
        target_source = inspect.getsource(target_function)
        target_globals = getattr(target_function, "__globals__", {})
        return canonical_law_expression(candidate_source, {}, parameters) == canonical_law_expression(
            target_source, target_globals, parameters
        )
    except (OSError, TypeError, SyntaxError, ValueError, KeyError):
        return False
