import ast
import math
import operator as op
from dataclasses import dataclass
from typing import Any, Dict

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
    expr = expr.strip()
    if not expr:
        raise SafeEvalError("Empty expression.")

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
            return ALLOWED_BINOPS[type(n.op)](_eval(n.left), _eval(n.right))

        if isinstance(n, ast.UnaryOp):
            if type(n.op) not in ALLOWED_UNARYOPS:
                raise SafeEvalError("Unary operator not allowed.")
            return ALLOWED_UNARYOPS[type(n.op)](_eval(n.operand))

        if isinstance(n, ast.Call):
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

        raise SafeEvalError("Unsupported expression.")

    result = _eval(node)
    return float(result)


# ----------------------------
# UI definitions
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


# ----------------------------
# State + callbacks
# ----------------------------

def init_state() -> None:
    st.session_state.setdefault("expr_input", "")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("history", [])  # list of (expr, shown)


def sync_from_input() -> None:
    # Called when user types in the text box
    st.session_state.error = None


def append_token(token: str) -> None:
    st.session_state.expr_input = (st.session_state.expr_input or "") + token
    st.session_state.error = None


def backspace() -> None:
    st.session_state.expr_input = (st.session_state.expr_input or "")[:-1]
    st.session_state.error = None


def clear_all() -> None:
    st.session_state.expr_input = ""
    st.session_state.result = None
    st.session_state.error = None


def evaluate() -> None:
    expr = (st.session_state.expr_input or "").strip()
    if not expr:
        st.session_state.error = "Enter an expression."
        st.session_state.result = None
        return

    try:
        val = safe_eval(expr)
        shown = str(int(val)) if val.is_integer() else str(val)
        st.session_state.result = shown
        st.session_state.error = None
        st.session_state.history.insert(0, (expr, shown))
        st.session_state.history = st.session_state.history[:15]
    except Exception as e:
        st.session_state.result = None
        st.session_state.error = str(e)


def use_history(expr: str) -> None:
    st.session_state.expr_input = expr
    st.session_state.error = None


def clear_history() -> None:
    st.session_state.history = []


# ----------------------------
# Streamlit app
# ----------------------------

st.set_page_config(page_title="Streamlit Calculator", page_icon="🧮", layout="centered")
init_state()

st.title("🧮 Calculator (Streamlit)")
st.caption("Supports: + - * / // % **, parentheses, and functions like sqrt(), sin(), log(). Use ^ for power.")

col1, col2 = st.columns([3, 1])
with col1:
    st.text_input(
        "Expression",
        key="expr_input",
        placeholder="e.g., (2 + 3) * 4^2, sqrt(16), log(8, 2)",
        on_change=sync_from_input,
    )
with col2:
    st.markdown("### ")
    st.button("Evaluate", type="primary", use_container_width=True, on_click=evaluate)

if st.session_state.result is not None:
    st.success(f"Result: **{st.session_state.result}**")

if st.session_state.error:
    st.error(st.session_state.error)

st.subheader("Quick functions")
chip_cols = st.columns(6)
for i, f in enumerate(FUNC_CHIPS):
    with chip_cols[i % 6]:
        st.button(f, use_container_width=True, on_click=append_token, args=(f,))

st.subheader("Keypad")
for row in BUTTON_ROWS:
    cols = st.columns(len(row))
    for c, btn in zip(cols, row):
        with c:
            if btn.value == "BACK":
                st.button(btn.label, use_container_width=True, help=btn.help or None, on_click=backspace)
            elif btn.value == "CLEAR":
                st.button(btn.label, use_container_width=True, help=btn.help or None, on_click=clear_all)
            elif btn.value == "EVAL":
                st.button(btn.label, use_container_width=True, help=btn.help or None, on_click=evaluate)
            else:
                st.button(btn.label, use_container_width=True, help=btn.help or None, on_click=append_token, args=(btn.value,))

with st.expander("History", expanded=False):
    if not st.session_state.history:
        st.write("No history yet.")
    else:
        for i, (expr, res) in enumerate(st.session_state.history, start=1):
            h1, h2, h3 = st.columns([5, 2, 2])
            with h1:
                st.write(f"{i}. `{expr}`")
            with h2:
                st.write(f"= **{res}**")
            with h3:
                st.button("Use", key=f"use_{i}", use_container_width=True, on_click=use_history, args=(expr,))
        st.divider()
        st.button("Clear history", on_click=clear_history)
