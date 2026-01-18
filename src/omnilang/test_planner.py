from omnilang.graph_builder import build_test_dsg
from dsg_exploration_sim.plotting import plot_layer, plot_frontiers
import matplotlib.pyplot as plt
import spark_dsg
from omnilang.solver import solve
from omnilang.streams import (
    Stream,
    find_streams_affecting_goal,
    expand_streams,
    eval_quantifier,
    get_symbol_to_type,
    get_symbols_from_facts,
)
from omnilang.mdp_definition import PddlDomain
from omnilang.parse_streams import parse_stream_file
from omnilang.parse_mdp import parse_domain_file
from omnilang.mdp_states import (
    State,
    Fact,
    Symbol,
    forall,
    Environment,
    generate,
    PartialState,
    ImproperQuantifiedSet,
)
import copy

from omnilang.rules import apply_rules
from dataclasses import dataclass
import math  # noqa


class FullDomain:
    def __init__(self, pddl_domain: PddlDomain, streams: list[Stream]):
        self.pddl_domain = pddl_domain
        self.streams = streams


@dataclass
class Problem:
    initial_state: State
    goal: PartialState


def load_full_domain(
    pddl_domain_path: str, stream_path: str, stream_functions: dict[str, callable] = {}
):
    streams = parse_stream_file(stream_path)
    for s in streams:
        if s.name in stream_functions:
            s.metadata_generator = stream_functions[s.name]
    pddl_domain = parse_domain_file(pddl_domain_path)
    return FullDomain(pddl_domain, streams)


def dsg_to_problem(G, initial_place, include_object_connections=False):
    facts = []

    for n in G.get_layer(spark_dsg.DsgLayers.OBJECTS).nodes:
        facts.append(Fact("obj", [Symbol(n.id.str())]))

    for n in G.get_layer(spark_dsg.DsgLayers.PLACES).nodes:
        attrs = n.attributes
        if not attrs.is_predicted and not attrs.real_place:
            facts.append(Fact("frontier", [Symbol(n.id.str())]))
            for m in n.connections():
                ns = spark_dsg.NodeSymbol(m).str()
                facts.append(Fact("connected", [Symbol(n.id.str()), Symbol(ns)]))

    traversability_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    for n in G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY).nodes:
        facts.append(Fact("place", [Symbol(n.id.str())]))
        for m in n.connections():
            if G.get_node(m).layer == traversability_layer_key:
                ns = spark_dsg.NodeSymbol(m).str()
                facts.append(Fact("connected", [Symbol(n.id.str()), Symbol(ns)]))

    facts.append(Fact("at", [Symbol(initial_place)]))
    facts.append(Fact("visited", [Symbol(initial_place)]))

    trav_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    if include_object_connections:
        for n in G.get_layer(spark_dsg.DsgLayers.OBJECTS).nodes:
            for m in n.connections():
                node = G.get_node(m)
                layer = node.layer
                if layer == trav_layer_key:
                    facts.append(
                        Fact("obj-at", [Symbol(n.id.str()), Symbol(node.id.str())])
                    )

    return State(facts)


def get_problem_for_goal(
    domain: FullDomain, planning_representation, goal, base_env=None
):
    relevant_streams = find_streams_affecting_goal(
        domain.streams, planning_representation, goal
    )

    generated_s0 = copy.deepcopy(planning_representation)
    generated_symbols = get_symbols_from_facts(planning_representation.facts)
    symbol_to_type = get_symbol_to_type(None, planning_representation)
    generated_env = Environment(base_env, generated_symbols, symbol_to_type)

    # Expand state until the goal is no longer true in the initial state
    max_depth = 10
    stream_evals_per_level = math.inf
    # stream_evals_per_level = 1
    for depth in range(max_depth):
        # restrict goal, check if goal in s0
        if isinstance(goal, ImproperQuantifiedSet):
            evaled_goal = eval_quantifier(generated_env, goal, generated_s0)
            explicit_goal = [g for g in generate(evaled_goal)]
        else:
            explicit_goal = list(
                goal.positive_facts
            )  # TODO: support negative goal conditions
        if explicit_goal not in generated_s0:
            break

        print(
            "generated_env positions: ",
            generated_env.get_symbols_with_metadata("position"),
        )
        print("expanding relevant streams: ", [s.name for s in relevant_streams])
        generated_env, generated_s0 = expand_streams(
            generated_env,
            relevant_streams,
            generated_s0,
            stream_evals_per_level=stream_evals_per_level,
        )

    apply_rules(generated_s0.facts)
    if isinstance(goal, ImproperQuantifiedSet):
        evaled_goal = eval_quantifier(generated_env, goal, generated_s0.facts)
    else:
        evaled_goal = goal

    return generated_env, Problem(generated_s0, evaled_goal)


if __name__ == "__main__":
    G = build_test_dsg()

    plot_layer(G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY))
    plot_frontiers(G)
    plt.show()

    goal = forall("p", "place", Fact("visited", [Symbol("p")]))

    planning_representation = dsg_to_problem(G, "t0")
    # planning_representation.facts.append(Fact("visited", [Symbol("t1")]))

    print("initial state: ", planning_representation)

    stream_path = "streams.pddl"
    pddl_domain_path = "test_domain.pddl"
    domain = load_full_domain(pddl_domain_path, stream_path)

    env, problem = get_problem_for_goal(domain, planning_representation, goal)

    plan = solve(domain.pddl_domain, problem.initial_state, problem.goal)

    domain2 = load_full_domain("pick_domain.pddl", stream_path)
    rep2 = dsg_to_problem(G, "t0", include_object_connections=True)
    rep2.facts.append(Fact("hand-free", []))
    goal2 = PartialState({Fact("obj-at", [Symbol("o1"), Symbol("t0")])}, set())
    env2, problem2 = get_problem_for_goal(domain2, rep2, goal2)
    plan2 = solve(domain2.pddl_domain, problem2.initial_state, problem2.goal)
