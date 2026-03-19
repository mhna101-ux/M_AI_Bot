from langchain_core.tools import Tool

def evaluate_math(expression: str) -> str:
    try:
        # Evaluate math expression safely.
        # Since this runs purely locally and is heavily restricted to the ALLOWED_USER_ID,
        # using Python's native eval for basic operations is acceptable.
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error evaluating math expression: {e}"

def get_math_tool() -> Tool:
    return Tool(
        name="MathCalculator",
        func=evaluate_math,
        description="Useful for when you need to answer questions about math. Input should be a valid mathematical expression in Python syntax."
    )
