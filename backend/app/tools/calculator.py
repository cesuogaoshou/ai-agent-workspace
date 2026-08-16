import ast
import math
import operator
from typing import Any

from backend.app.tools.base import ToolResult


class ExpressionTooLarge(ValueError):
    pass


class CalculatorTool:
    name = "calculator"
    description = "Evaluate deterministic arithmetic expressions."
    requires_approval = False
    _MAX_AST_NODES = 50
    _MAX_ABS_RESULT = 1_000_000_000_000
    _MAX_ABS_EXPONENT = 100
    _UNSUPPORTED_SYNTAX_ERROR = "Expression contains unsupported syntax."
    _TOO_LARGE_ERROR = "Expression result is too large."
    parameters = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        expression = str(arguments.get("expression", ""))
        try:
            tree = ast.parse(expression, mode="eval")
            self._validate_complexity(tree)
            result = self._validate_result(self._eval(tree.body))
        except ExpressionTooLarge:
            return ToolResult(ok=False, error=self._TOO_LARGE_ERROR)
        except ValueError as exc:
            return ToolResult(ok=False, error=str(exc))
        except Exception:
            return ToolResult(ok=False, error="Expression could not be evaluated.")
        return ToolResult(ok=True, output={"result": result})

    def _eval(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            return self._validate_constant(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            left = self._eval(node.left)
            right = self._eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > self._MAX_ABS_EXPONENT:
                raise ExpressionTooLarge(self._TOO_LARGE_ERROR)
            return self._validate_result(self._operators[type(node.op)](left, right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._operators:
            return self._validate_result(
                self._operators[type(node.op)](self._eval(node.operand))
            )
        raise ValueError(self._UNSUPPORTED_SYNTAX_ERROR)

    def _validate_complexity(self, tree: ast.AST) -> None:
        if sum(1 for _ in ast.walk(tree)) > self._MAX_AST_NODES:
            raise ExpressionTooLarge(self._TOO_LARGE_ERROR)

    def _validate_constant(self, value: object) -> int | float:
        if type(value) not in (int, float):
            raise ValueError(self._UNSUPPORTED_SYNTAX_ERROR)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(self._UNSUPPORTED_SYNTAX_ERROR)
        return self._validate_result(value)

    def _validate_result(self, value: int | float) -> int | float:
        if isinstance(value, float) and not math.isfinite(value):
            raise ExpressionTooLarge(self._TOO_LARGE_ERROR)
        if abs(value) > self._MAX_ABS_RESULT:
            raise ExpressionTooLarge(self._TOO_LARGE_ERROR)
        return value
