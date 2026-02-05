import ast
import math
import operator as op
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import streamlit as st


# ----------------------------
# Safe expression evaluator
# ----------------------------

ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

ALLOWED_UNARYOPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

# Map of allowed names/functions
SAFE_NAMES: Dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,

    "abs": abs,
    "round": round,

    "sqrt": math.sqrt,
    "log": math.log,      # log(x, base) supported
    "log10": math.log10,
    "ln": math.log,       # alias
    "exp": math.exp,

    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,

    "degrees": math.degrees,
    "radians": math.radians,

    "factorial": math.factorial,
    "floor": math.floor,
    "ceil": math.ceil,
}


class SafeEvalError(Exception):
    pass


def safe_eval(expr: str) -> float:
    """
    Evaluate a math expression safely using AST.
    Supports numbers, parentheses, + - * / // % **, unary +/-, and approved functions/constants.
    """
    expr = expr.strip()
    if not expr:
        raise SafeEvalError("Empty expression.")

    # Convenience: allow ^ as power (like many calculators)
    expr = expr.replace("^", "**")

    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise SafeEvalError("Invalid syntax.") from e

    def _eval(n: ast.AST) -> Any:
        if isinstance(n, ast.Expression):
            return _eval(n.body)

        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return n.value
            raise SafeEvalError("Only numeric constants are allowed.")

        if isinstance(n, ast.BinOp):
            if type(n.op) not in ALLOWED_BINOPS:
                raise SafeEvalError("Operator not allowed.")
            left = _eval(n.left)
            right = _eval(n.right)
            return ALLOWED_BINOPS[type(n.op)](left, right)

        if isinstance(n, ast.UnaryOp):
            if type(n.op) not in ALLOWED_UNARYOPS:
                raise SafeEvalError("Unary operator not allowed.")
            operand = _eval(n.operand)
            return ALLOWED_UNARYOPS[type(n.op)](operand)

        if isinstance(n, ast.Call):
            # Only allow calls like func(...)
            if not isinstance(n.func, ast.Name):
                raise SafeEvalError("Only simple function calls are allowed.")
            func_name = n.func.id
            func = SAFE_NAMES.get(func_name)
            if func is None or not callable(func):
                raise SafeEvalError(f"Function '{func_name}' is not allowed.")
            args = [_eval(a) for a in n.args]
            kwargs = {kw.arg: _eval(kw.value) for kw in n.keywords if kw.arg is not None}
            return func(*args, **kwargs)

        if isinstance(n, ast.Name):
            if n.id in SAFE_NAMES and not callable(SAFE_NAMES[n.id]):
                return SAFE_NAMES[n.id]
            raise SafeEvalError(f"Name '{n.id}' is not allowed.")

        if isinstance(n, ast.Tuple) or isinstance(n, ast.List) or isinstance(n, ast.Dict):
            raise SafeEvalError("Collections are not allowed.")

        raise SafeEvalError("Unsupported expression.")

    result = _eval(node)
    try:
        return float(result)
    except Exception as e:
        raise SafeEvalError("Could not compute result.") from e


# ----------------------------
# UI helpers
# ----------------------------

@dataclass
class CalcButton:
    label: str
    value: str
    help: str = ""


BUTTON_ROWS = [
    [CalcButton("7", "7"), CalcButton("8", "8"), CalcButton("9", "9"), CalcButton("÷", "/"), CalcButton("⌫", "BACK")],
    [CalcButton("4", "4"), CalcButton("5", "5"), CalcButton("6", "6"), CalcButton("×", "*"), CalcButton("(", "(")],
    [CalcButton("1", "1"), CalcButton("2", "2"), CalcButton("3", "3"), CalcButton("-", "-"), CalcButton(")", ")")],
    [CalcButton("0", "0"), CalcButton(".", "."), CalcButton("%", "%"), CalcButton("+", "+"), CalcButton("C", "CLEAR")],
    [CalcButton("π", "pi"), CalcButton("e", "e"), CalcButton("^", "^"), CalcButton("√", "sqrt("), CalcButton("=", "EVAL")],
]

FUNC_CHIPS = [
    "sin(", "cos(", "tan(",
    "asin(", "acos(", "atan(",
    "log(", "log10(", "ln(",
    "exp(", "factorial(",
    "degrees(", "radians(",
    "abs(", "round(",
]


def init_state() -> None:
    if "expr" not in st.session_state:
        st.session_state.expr = ""
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "history" not in st.session_state:
        st.session_state.history = []  # list[tuple[str, str]]


def append_to_expr(token: str) -> None:
    st.session_state.expr += token


def backspace() -> None:
    st.session_state.expr = st.session_state.expr[:-1]


def clear_all() -> None:
    st.session_state.expr = ""
    st.session_state.result = None
    st.session_state.error = None


def evaluate() -> None:
    expr = st.session_state.expr.strip()
    if not expr:
        st.session_state.error = "Enter an expression."
        st.session_state.result = None
        return

    try:
        val = safe_eval(expr)
        # Nice formatting: avoid trailing .0 for integers
        shown = str(int(val)) if val.is_integer() else str(val)
        st.session_state.result = shown
        st.session_state.error = None
        st.session_state.history.insert(0, (expr, shown))
        st.session_state.history = st.session_state.history[:15]
    except Exception as e:
        st.session_state.result = None
        st.session_state.error = str(e)


# ----------------------------
# Streamlit app
# ----------------------------

st.set_page_config(page_title="Streamlit Calculator", page_icon="🧮", layout="centered")
init_state()

st.title("🧮 Calculator (Streamlit)")
st.caption("Type an expression or use the buttons. Supports: + - * / // % **, parentheses, and functions like sqrt(), sin(), log().")

with st.container():
    col1, col2 = st.columns([3, 1])

    with col1:
        st.text_input(
            "Expression",
            key="expr",
            placeholder="e.g., (2 + 3) * 4^2, sqrt(16), log(8, 2)",
            label_visibility="visible",
        )

    with col2:
        st.markdown("### ")
        if st.button("Evaluate", type="primary", use_container_width=True):
            evaluate()

if st.session_state.result is not None:
    st.success(f"Result: **{st.session_state.result}**")

if st.session_state.error:
    st.error(st.session_state.error)

# Function chips
st.subheader("Quick functions")
chip_cols = st.columns(6)
for i, f in enumerate(FUNC_CHIPS):
    with chip_cols[i % 6]:
        if st.button(f, use_container_width=True):
            append_to_expr(f)

st.subheader("Keypad")
for row in BUTTON_ROWS:
    cols = st.columns(len(row))
    for c, btn in zip(cols, row):
        with c:
            if st.button(btn.label, use_container_width=True, help=btn.help or None):
                if btn.value == "BACK":
                    backspace()
                elif btn.value == "CLEAR":
                    clear_all()
                elif btn.value == "EVAL":
                    evaluate()
                else:
                    append_to_expr(btn.value)

# History
with st.expander("History", expanded=False):
    if not st.session_state.history:
        st.write("No history yet.")
    else:
        for i, (expr, res) in enumerate(st.session_state.history, start=1):
            hcol1, hcol2, hcol3 = st.columns([5, 2, 2])
            with hcol1:
                st.write(f"{i}. `{expr}`")
            with hcol2:
                st.write(f"= **{res}**")
            with hcol3:
                if st.button("Use", key=f"use_{i}", use_container_width=True):
                    st.session_state.expr = expr

        st.divider()
        if st.button("Clear history"):
            st.session_state.history = []
