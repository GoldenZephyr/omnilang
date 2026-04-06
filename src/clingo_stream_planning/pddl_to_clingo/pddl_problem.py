import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import get_static_predicates


def generate_primitive_constants(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    symbols = oml.get_symbols_from_facts(state.facts)
    lines = ["% (Constant) Primitives"]
    for symbol in symbols:
        type = env.get_object_type(symbol)
        if type is None:
            type = "object"
        lines.append(f'constant(constant("{symbol}")).')
        lines.append(f'has(constant("{symbol}"), type("{type}")).')
    return lines


def generate_compound_constant(f: oml.Fact):
    kernel = (f'"{f.head}"',)
    for s in f.body:
        kernel += (f'constant("{s.identifier}")',)
    kernel_str = ",".join(kernel)
    lines = [f"staticFact(({kernel_str}))."]
    return lines


def generate_compound_constants(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    lines = ["% (Constant) Initial state"]
    static_predicates = get_static_predicates(env, domain, state)
    for f in state.facts:
        if f.head not in static_predicates:
            continue
        lines += generate_compound_constant(f)
    return lines

    return lines


def generate_initial_state_variable(f: oml.Fact):
    kernel = (f'"{f.head}"',)
    for s in f.body:
        kernel += (f'constant("{s.identifier}")',)
    kernel_str = ",".join(kernel)
    lines = [
        f"initialState(variable(({kernel_str}))), value(variable(({kernel_str})), true))."
    ]
    return lines


def generate_initial_state_variables(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    lines = ["% (Variable) Initial state"]
    static_predicates = get_static_predicates(env, domain, state)
    for f in state.facts:
        if f.head in static_predicates:
            continue
        lines += generate_initial_state_variable(f)
    lines.append(
        "initialState(X, value(X, false)) :- variable(X), not initialState(X, value(X, true))."
    )
    return lines


def compile_pddl_instance(
    env: oml.Environment, domain: oml.PddlDomain, state: oml.State
):
    lines = generate_primitive_constants(env, domain, state)
    lines += generate_compound_constants(env, domain, state)
    lines += generate_initial_state_variables(env, domain, state)
    lines += generate_goal(env, domain, state)
    return lines
