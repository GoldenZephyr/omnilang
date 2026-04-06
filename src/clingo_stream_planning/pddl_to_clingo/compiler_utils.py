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


def get_static_predicates(env, domain: oml.FullDomain, state, include_groups=True):
    static_predicates = domain.pddl_domain.predicates
    for action in domain.pddl_domain.actions:
        for effect in action.positive_effect + action.negative_effect:
            if effect.head in static_predicates:
                static_predicates.remove(effect.head)
    if include_groups:
        for action in domain.pddl_domain.group_actions:
            for effect in action.positive_effect + action.negative_effect:
                if effect.head in static_predicates:
                    static_predicates.remove(effect.head)
    return static_predicates
