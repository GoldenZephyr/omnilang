import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.utils import generate_utils
from clingo_stream_planning.pddl_to_clingo.types import generate_type_hierarchy
from clingo_stream_planning.pddl_to_clingo.variables import generate_variables
from clingo_stream_planning.pddl_to_clingo.actions import (
    generate_normal_actions,
    generate_group_actions,
)
from clingo_stream_planning.pddl_to_clingo.streams import (
    compile_stream_definitions,
    compile_stream_instances,
)
from clingo_stream_planning.pddl_to_clingo.derived_streams import (
    compile_derived_streams,
)
from clingo_stream_planning.pddl_to_clingo.pddl_problem import compile_pddl_instance
from clingo_stream_planning.pddl_to_clingo.derived_predicates import (
    generate_derived_predicates,
)
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    ClingoPddlCompilerOptions,
)


def compile_domain(
    options: ClingoPddlCompilerOptions,
    env: oml.Environment,
    domain: oml.FullDomain,
    state: oml.State,
):
    """This is for compiling the domain. BUT, some optimizations might be
    applied based on the state
    """
    lines = generate_utils(env, domain, state)
    lines.append("\n")
    lines += generate_type_hierarchy(env, domain, state)
    lines.append("\n")
    lines += generate_variables(
        env,
        domain,
        state,
        options.enable_static_optimizations,
        options.enable_derived_streams,
    )
    lines.append("\n")
    lines += generate_derived_predicates(env, domain, state)
    lines.append("\n")
    lines += generate_normal_actions(env, domain, state)
    lines.append("\n")
    if options.enable_groups:
        lines += generate_group_actions(env, domain, state)

    return lines


def compile_optimization_objectives(env, domain, state):
    # Currently, generate a plan in the "maximally feasible world"
    lines = ["% World objective to optimize"]
    lines += ["#maximize {1, X : inworld(X)}."]
    lines += ["#minimize {2, X : ingroup(_, X)}."]
    return lines


def add_show_statements(options):
    lines = ["% Facts to show"]
    lines += ["trueInitialState(Var) :- initialState(Var, value(Var, true))."]
    lines.append("#show trueInitialState/1.")
    if options.enable_streams:
        lines.append("#show generated_by/2.")
        lines.append("#show inworld/1.")
        lines.append("#show stream_generated/1.")
        lines.append("#show stream_derived/1.")
    if options.enable_groups:
        lines.append("#show ingroup/2.")
        lines.append("#show group_chosen/3.")

    lines.append("#show w0/1.")

    return lines


def compile_problem(
    options: ClingoPddlCompilerOptions,
    env: oml.Environment,
    domain: oml.FullDomain,
    problem: oml.Problem,
):
    # TODO: need to normalize complex goals into derived streams + simple goal
    lines = compile_domain(options, env, domain, problem.initial_state)
    if options.enable_streams:
        lines += compile_stream_definitions(env, domain, problem.initial_state)
        lines += ["\n"]
    if options.enable_derived_streams:
        lines += compile_derived_streams(env, domain, problem.initial_state)

    lines += compile_pddl_instance(options, env, domain, problem)

    if options.enable_streams:
        lines += compile_stream_instances(env, domain, problem.initial_state)
        lines += ["\n"]
    if options.enable_optimization:
        lines += compile_optimization_objectives(env, domain, problem.initial_state)
        lines += ["\n"]

    lines += add_show_statements(options)
    return lines
