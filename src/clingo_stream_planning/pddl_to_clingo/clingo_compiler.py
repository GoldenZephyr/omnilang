import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.utils import generate_utils
from clingo_stream_planning.pddl_to_clingo.types import generate_type_hierarchy
from clingo_stream_planning.pddl_to_clingo.variables import generate_variables
from clingo_stream_planning.pddl_to_clingo.actions import (
    generate_normal_actions,
    generate_group_actions,
)
from clingo_stream_planning.pddl_to_clingo.streams import compile_stream_definitions
from clingo_stream_planning.pddl_to_clingo.derived_streams import (
    compile_derived_streams,
)
from clingo_stream_planning.pddl_to_clingo.pddl_problem import compile_pddl_instance

from dataclasses import dataclass


@dataclass
class ClingoPddlCompilerOptions:
    enable_streams: bool
    enable_derived_streams: bool
    enable_groups: bool
    enable_optimization: bool
    enable_static_optimizations: bool
    enable_incremental: bool


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
    lines += generate_type_hierarchy(env, domain, state)
    lines += generate_variables(env, domain, state)
    lines += generate_derived_predicates(
        env, domain, state
    )  # TODO: copy from directory above
    lines += generate_normal_actions(env, domain, state)
    if options.enable_groups:
        lines += generate_group_actions(env, domain, state)

    return lines


def compile_optimization_objectives(env, domain, state):
    # Currently, generate a plan in the "maximally feasible world"
    return ["#maximize {1, X : inworld(X)}."]


# def add_show_statements(options):
#    return []


def compile_problem(
    options: ClingoPddlCompilerOptions,
    env: oml.Environment,
    domain: oml.FullDomain,
    state: oml.State,
):
    # TODO: need to normalize complex goals into derived streams + simple goal
    lines = compile_domain(env, domain, state)
    if options.enable_streams:
        lines += compile_stream_definitions(env, domain, state)
    if options.enable_derived_streams:
        lines += compile_derived_streams(env, domain, state)

    lines += compile_pddl_instance(env, domain, state)

    if options.enable_streams:
        lines += compile_stream_instances(env, domain, state)
    if options.enable_optimization:
        lines += compile_optimization_objectives(env, domain, state)

    lines += add_show_statements(options)
