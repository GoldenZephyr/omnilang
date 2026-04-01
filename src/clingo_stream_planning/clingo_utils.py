import omnilang as oml


def to_lifted_clingo_string(fact: oml.Fact):
    head = fact.head.replace("-", "_")
    return f"{head}({', '.join([variable_to_clingo(p) for p in fact.body])})"


def to_clingo_string(fact: oml.Fact):
    head = fact.head.replace("-", "_")
    body = ", ".join([f'constant("{p.identifier}")' for p in fact.body])
    return f"{head}({body})"


def variable_to_clingo(symbol: oml.Symbol) -> str:
    s = symbol.identifier.upper()
    if s.startswith("?") or s.startswith("&"):
        s = s[1:]
    return s


def to_clingo_type_string(var, type):
    return f'has({var}, type("{type}"))'


def to_clingo_group_type_string(var, type):
    return f'has({var}, grouptype("{type}"))'
