import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    get_static_predicates,
    symbol_to_clingo,
)
from clingo_stream_planning.pddl_to_clingo.derived_predicates import (
    derived_predicate_to_clingo,
    build_derived_variable_and_constraints,
)


def compile_pddl_instance(
    env: oml.Environment,
    domain: oml.PddlDomain,
    problem: oml.Problem,
):
    lines = ["%% PDDL Instance"]
    lines += generate_primitive_constants(env, domain, problem.initial_state)
    lines += ["\n"]
    lines += generate_compound_constants(env, domain, problem.initial_state)
    lines += ["\n"]
    lines += generate_initial_state_variables(env, domain, problem.initial_state)
    lines += ["\n"]
    lines += generate_goal(env, domain, problem.goal)
    lines += ["\n"]
    return lines


def derived_predicate_to_variable(dp: oml.DerivedPredicate):
    derived_var, _ = build_derived_variable_and_constraints(
        dp.name, dp.params, dp.types
    )
    return f"derivedVariable({derived_var})"


def fact_to_kernel(fact: oml.Fact | oml.NegatedFact):
    return ", ".join(
        (f'"{fact.head}"',) + tuple(symbol_to_clingo(s) for s in fact.body)
    )


def generate_goal(env: oml.Environment, domain: oml.FullDomain, goal):
    lines = ["% goal"]
    if isinstance(goal, oml.Fact):
        kernel = fact_to_kernel(goal)
        goal_var = f"variable(({kernel}))"
        val = "true"
    elif isinstance(goal, oml.NegatedFact):
        kernel = fact_to_kernel(goal)
        goal_var = f"variable(({kernel}))"
        val = "false"
    else:
        print(goal)
        assert isinstance(goal, oml.Formula)
        val = "true"
        quantified_vars = goal.get_quantified_variables()
        all_vars = goal.get_params_matching(
            lambda x: isinstance(x, oml.Symbol) and x.identifier.startswith("?")
        )
        params = [p for p in all_vars if p not in quantified_vars]

        types = [env.get_object_type(s) for s in params]
        dp = oml.DerivedPredicate("goal-dp", params, types, goal)

        aux_dp, original_dp = derived_predicate_to_clingo(dp)
        lines += aux_dp + original_dp
        dp_kernel = (
            "goal-dp"  # Goal derived predicate can't have any top-level free variables
        )
        goal_var = f'variable("{dp_kernel}")'

    goal = f"""goal({goal_var}, value({goal_var}, {val}))."""
    lines.append(goal)
    return lines


def generate_primitive_constants(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    symbols = oml.get_symbols_from_facts(state.facts)
    lines = ["% (Constant) Primitives"]
    for symbol in symbols:
        type = env.get_object_type(symbol)
        if type is None:
            type = "object"
        lines.append(f'constant(constant("{symbol.identifier}")).')
        lines.append(f'has(constant("{symbol.identifier}"), type("{type}")).')
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
        f"initialState(variable(({kernel_str})), value(variable(({kernel_str})), true))."
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
    lines += ["\n"]
    lines.append(
        "initialState(X, value(X, false)) :- variable(X), not initialState(X, value(X, true))."
    )
    lines += [
        "w0(Kernel) :- initialState(variable(Kernel), value(variable(Kernel), true))."
    ]
    lines += [
        "initialState(variable(Kernel), value(variable(Kernel), true)) :- variable(variable(Kernel)), w0(Kernel)."
    ]
    lines += [
        "initialState(variable(Kernel), value(variable(Kernel), false)) :- variable(variable(Kernel)), -w0(Kernel)."
    ]
    return lines
