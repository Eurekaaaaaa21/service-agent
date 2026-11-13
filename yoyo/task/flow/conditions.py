from typing import Any


class ConditionEvaluator:
    def evaluate(
            self,
            expression: str,
            data: dict[str, Any],
    ) -> bool:
        return bool(eval(
            expression,
            {"__builtins__": {}},
            data,
        ))
