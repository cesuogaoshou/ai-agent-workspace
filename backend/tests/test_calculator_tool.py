from backend.app.tools.calculator import CalculatorTool


def test_calculator_adds_numbers() -> None:
    result = CalculatorTool().execute({"expression": "2 + 3 * 4"})
    assert result.ok is True
    assert result.output == {"result": 14}


def test_calculator_rejects_unsafe_expression() -> None:
    result = CalculatorTool().execute({"expression": "__import__('os').system('dir')"})
    assert result.ok is False
    assert result.error == "Expression contains unsupported syntax."


def test_calculator_rejects_bool_constants() -> None:
    result = CalculatorTool().execute({"expression": "True + 1"})
    assert result.ok is False
    assert result.error == "Expression contains unsupported syntax."


def test_calculator_rejects_non_finite_numeric_constants() -> None:
    result = CalculatorTool().execute({"expression": "1e309"})
    assert result.ok is False
    assert result.error == "Expression contains unsupported syntax."


def test_calculator_rejects_excessive_exponentiation() -> None:
    result = CalculatorTool().execute({"expression": "2 ** 1000000"})
    assert result.ok is False
    assert result.error == "Expression result is too large."
