import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    get_static_predicates,
    to_clingo_type_string,
    variable_to_clingo,
)


def generate_variable(domain_predicate: oml.DomainPredicate):
    variable = (f'"{domain_predicate.head}"',)
    for p in domain_predicate.body:
        variable += variable_to_clingo(p)

    variable_string = f'variable(variable(({", ".join(variable)})))'

    type_strings = []
    for parm, types in zip(domain_predicate.body, domain_predicate.type_restrictions):
        match types:
            case []:
                type = "object"
            case [t]:
                type = t
            case _:
                raise Exception(
                    f"Domain predicates only support a single type restriction. {domain_predicate.head} {parm} was given: {types}"
                )
        var = variable_to_clingo(parm)
        type_strings.append(to_clingo_type_string(var, type))
        type_strings.append("inworld({var})")

    type_constraints = ", ".join(type_strings)
    line = f"{variable_string} :- {type_constraints}."
    return [line]


def generate_variables(
    env: oml.Environment,
    domain: oml.FullDomain,
    state: oml.State,
    enable_static_optimization: bool = True,
):
    lines = ["% variables"]
    if enable_static_optimization:
        static_domain_predicates = get_static_predicates(env, domain.pddl_domain, state)
    else:
        static_domain_predicates = set()

    for dp in domain.pddl_domain.predicates:
        if dp.head in static_domain_predicates:
            continue
        lines += generate_variable(dp)

    lines.append("contains(X, value(X, B)) :- variable(X), boolean(B).")
    return lines
