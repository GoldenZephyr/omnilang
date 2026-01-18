# ruff: noqa: F811
from plum import dispatch

INDENT = "    "


@dispatch
def indent(level: int, s: str):
    return indent_str(level) + s


@dispatch
def indent(level: int, strings: list[str]):
    return [indent(level, s) for s in strings]


def indent_str(level: int) -> str:
    return INDENT * level
