import omnilang as oml
from dataclasses import dataclass


@dataclass
class ClingoPddlCompilerOptions:
    enable_streams: bool = True
    enable_derived_streams: bool = True
    enable_optimization: bool = False
    enable_static_optimizations: bool = True
    enable_groups: bool = True
    enable_incremental: bool = False


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


def symbol_to_clingo(symbol: oml.Symbol) -> str:
    if symbol.identifier[0] not in ["?", "&"]:
        return f'constant("{symbol.identifier}")'
    else:
        s = symbol.identifier.upper()
        return s[1:]


def to_clingo_type_string(var, type):
    return f'has({var}, type("{type}"))'


def to_clingo_group_type_string(var, type):
    return f'has({var}, grouptype("{type}"))'


def to_w0_constraint(f: oml.Fact):
    kernel = ", ".join((f'"{f.head}"',) + tuple(symbol_to_clingo(s) for s in f.body))
    return f"w0(({kernel}))"


def get_static_predicates(env, domain: oml.FullDomain, state, include_groups=True):
    name_to_pred = {p.head: p for p in domain.pddl_domain.predicates}
    static_predicates = set(name_to_pred.keys())
    for action in domain.pddl_domain.actions:
        for effect in action.positive_effect + action.negative_effect:
            if effect.head in static_predicates:
                static_predicates.remove(effect.head)

    for dp in domain.pddl_domain.derived_predicates:
        static_predicates.remove(dp.name)

    if include_groups:
        for action in domain.pddl_domain.group_actions:
            for effect in action.positive_effect + action.negative_effect:
                if effect.head in static_predicates:
                    static_predicates.remove(effect.head)
    return [name_to_pred[p] for p in static_predicates]
