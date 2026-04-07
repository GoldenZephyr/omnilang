import spark_dsg
from omnilang.streams import (
    Stream,
    DerivedStreamFacts,
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
    PartialState,
    ImproperQuantifiedSet,
)
from omnilang.environment import Environment
from omnilang.mdp_state_operations import generate
import copy

from omnilang.rules import apply_rules
from dataclasses import dataclass
import math
import logging
from typing import Optional
from dsg_exploration_sim.action_and_states import SimulationState

logger = logging.getLogger(__name__)


class FullDomain:
    def __init__(
        self,
        pddl_domain: PddlDomain,
        streams: list[Stream],
        derived_stream_facts: Optional[list[DerivedStreamFacts]] = None,
    ):
        self.pddl_domain = pddl_domain
        self.streams = streams
        self.derived_stream_facts = derived_stream_facts

    def lookup_stream(self, stream_name):
        for s in self.streams:
            if s.name == stream_name:
                return s


@dataclass
class Problem:
    initial_state: State
    goal: PartialState


def load_full_domain(
    pddl_domain_path: str,
    stream_path: str | list[str],
    stream_functions: dict[str, callable] = {},
):
    streams = []
    derived_stream_facts = []
    match stream_path:
        case str():
            streams, derived_stream_facts = parse_stream_file(stream_path)
        case list() | tuple():
            for fn in stream_path:
                s, d = parse_stream_file(fn)
                streams += s
                derived_stream_facts += d

    print("Streams: ")
    print(streams)
    print(derived_stream_facts)
    for s in streams:
        if s.name in stream_functions:
            s.metadata_generator = stream_functions[s.name]
    pddl_domain = parse_domain_file(pddl_domain_path)
    return FullDomain(pddl_domain, streams, derived_stream_facts)


def augment_planning_representation(
    G, current_state: SimulationState, planning_rep: State
):
    for vn in current_state.visited_nodes:
        sym = spark_dsg.NodeSymbol(vn).str()
        planning_rep.facts.add(Fact("visited", [Symbol(sym)]))

    if True:
        for n in G.base_dsg.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY).nodes:
            sym = n.id.str()
            planning_rep.facts.add(Fact("observed", [Symbol(sym)]))

    if len(current_state.held_objects) == 0:
        planning_rep.facts.add(Fact("hand-free", []))

    for o in current_state.held_objects:
        sym = spark_dsg.NodeSymbol(o).str().lower()
        planning_rep.facts.add(Fact("holding", [Symbol(sym)]))


def objects_to_pddl(
    G: spark_dsg.DynamicSceneGraph,
    special_object_categories,
    include_object_connections,
):
    symbol_to_type = {}
    facts = set()
    for n in G.get_layer(spark_dsg.DsgLayers.OBJECTS).nodes:
        node_layer = n.layer.layer
        node_partition = n.layer.partition
        category = G.get_labelspace(node_layer, node_partition).get_node_category(n)
        symbol = Symbol(n.id.str().lower())
        if category in special_object_categories:
            t = category
        else:
            t = "obj"

        symbol_to_type[symbol] = t
        facts.add(Fact("observed", [symbol]))

    trav_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    if include_object_connections:
        for n in G.get_layer(spark_dsg.DsgLayers.OBJECTS).nodes:
            for m in n.connections():
                node = G.get_node(m)
                layer = node.layer
                if layer == trav_layer_key:
                    facts.add(
                        Fact(
                            "obj-at",
                            [Symbol(n.id.str().lower()), Symbol(node.id.str().lower())],
                        )
                    )
    return symbol_to_type, facts


def places_to_pddl(G: spark_dsg.SceneGraph):
    # Primarily for frontiers
    symbol_to_type = {}
    facts = set()
    traversability_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    for n in G.get_layer(spark_dsg.DsgLayers.PLACES).nodes:
        attrs = n.attributes
        if not attrs.is_predicted and not attrs.real_place:
            frontier_symbol = Symbol(n.id.str().lower())
            symbol_to_type[frontier_symbol] = "frontier"
            # NOTE: currently (3D) Places/Frontiers can't be connected to each other
            for m in n.connections():
                if G.get_node(m).layer == traversability_layer_key:
                    ns = spark_dsg.NodeSymbol(m).str().lower()
                    facts.add(Fact("connected", [Symbol(ns), frontier_symbol]))

    return symbol_to_type, facts


def traversability_to_pddl(G: spark_dsg.SceneGraph):
    symbol_to_type = {}
    facts = set()
    traversability_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    for n in G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY).nodes:
        place_symbol = Symbol(n.id.str().lower())
        symbol_to_type[place_symbol] = "place"
        for m in n.connections():
            if G.get_node(m).layer == traversability_layer_key:
                ns = spark_dsg.NodeSymbol(m).str().lower()
                facts.add(Fact("connected", [place_symbol, Symbol(ns)]))
    return symbol_to_type, facts


def regions_to_pddl(G: spark_dsg.SceneGraph):
    symbol_to_type = {}
    facts = set()
    for n in G.get_layer(spark_dsg.DsgLayers.ROOMS).nodes:
        regions_symbol = Symbol(n.id.str().lower())
        symbol_to_type[regions_symbol] = "region"

    trav_layer_key = G.get_layer_key(spark_dsg.DsgLayers.TRAVERSABILITY)
    region_layer_key = G.get_layer_key(spark_dsg.DsgLayers.ROOMS)
    for n in G.get_layer(spark_dsg.DsgLayers.ROOMS).nodes:
        room_symbol = Symbol(n.id.str().lower())
        for m in n.connections():
            node = G.get_node(m)
            layer = node.layer
            if layer == trav_layer_key:
                facts.add(
                    Fact(
                        "place-in-region",
                        [Symbol(node.id.str().lower()), room_symbol],
                    )
                )
            elif layer == region_layer_key:
                ns = node.id.str().lower()
                facts.add(Fact("region-connected", [room_symbol, Symbol(ns)]))

    return symbol_to_type, facts


def make_type_predicates(symbol_to_type: dict[Symbol, str]):
    facts = set()
    for symbol, type in symbol_to_type.items():
        facts.add(Fact(type, [symbol]))
    return facts


def types_and_facts_from_generators(G, generators):
    facts = set()
    symbol_to_type = {}

    for gen in generators:
        layer_types, layer_facts = gen(G)
        symbol_to_type |= layer_types
        facts |= layer_facts
    return symbol_to_type, facts


def dsg_to_region_problem(
    G,
    initial_place,
    special_object_categories=["food"],
):
    pddl_generators = [
        places_to_pddl,
        traversability_to_pddl,
        lambda g: objects_to_pddl(g, special_object_categories, True),
        regions_to_pddl,
    ]
    symbol_to_type, facts = types_and_facts_from_generators(G, pddl_generators)

    facts.add(Fact("at", [Symbol(initial_place)]))
    facts.add(Fact("visited", [Symbol(initial_place)]))

    return symbol_to_type, State(facts)


def dsg_to_problem(
    G,
    initial_place,
    include_object_connections=False,
    special_object_categories=["food"],
    types_as_predicates=False,
):
    pddl_generators = [
        places_to_pddl,
        traversability_to_pddl,
        lambda g: objects_to_pddl(
            g, special_object_categories, include_object_connections
        ),
    ]
    symbol_to_type, facts = types_and_facts_from_generators(G, pddl_generators)

    facts.add(Fact("at", [Symbol(initial_place)]))
    facts.add(Fact("visited", [Symbol(initial_place)]))

    if types_as_predicates:
        type_facts = make_type_predicates(symbol_to_type)
        facts |= type_facts

    return symbol_to_type, State(facts)


def generate_bindable_world(
    domain: FullDomain, env: Environment, state: State, goal: ImproperQuantifiedSet
):
    assert goal.quantifier == "exists"
    print("generating bindable world")
    # relevant_streams = find_streams_affecting_goal(
    #     domain.pddl_domain, domain.streams, env, state, goal
    # )
    relevant_streams = set(domain.streams)
    generated_s0 = copy.deepcopy(state)
    generated_symbols = get_symbols_from_facts(state.facts)
    symbol_to_type = get_symbol_to_type(domain.pddl_domain, state)
    generated_env = Environment(env, generated_symbols, symbol_to_type)

    max_depth = 10
    stream_evals_per_level = math.inf
    # stream_evals_per_level = 1
    for depth in range(max_depth):
        # restrict goal, check if goal in s0
        evaled_goal = eval_quantifier(generated_env, goal, generated_s0)
        explicit_goal = [g for g in generate(evaled_goal)]
        if len(explicit_goal) > 0:
            break

        generated_env, generated_s0 = expand_streams(
            generated_env,
            domain.pddl_domain,
            relevant_streams,
            generated_s0,
            stream_evals_per_level=stream_evals_per_level,
        )
    return generated_env, generated_s0


def generate_unsatisfying_consistent_world(
    domain: FullDomain, env: Environment, state: State, goal: ImproperQuantifiedSet
):
    relevant_streams = find_streams_affecting_goal(
        domain.pddl_domain, domain.streams, env, state, goal
    )

    generated_s0 = copy.deepcopy(state)
    generated_symbols = get_symbols_from_facts(state.facts)
    symbol_to_type = get_symbol_to_type(domain.pddl_domain, state)
    generated_env = Environment(env, generated_symbols, symbol_to_type)

    # Expand state until the goal is no longer true in the initial state
    max_depth = 10
    stream_evals_per_level = math.inf
    # stream_evals_per_level = 1
    for depth in range(max_depth):
        # restrict goal, check if goal in s0
        logger.info(f"Grounding goal to symbols: {str(generated_env.symbols)}")
        evaled_goal = eval_quantifier(generated_env, goal, generated_s0)
        explicit_goal = [g for g in generate(evaled_goal)]

        if explicit_goal not in generated_s0:
            break
        generated_env, generated_s0 = expand_streams(
            generated_env,
            domain.pddl_domain,
            relevant_streams,
            generated_s0,
            stream_evals_per_level=stream_evals_per_level,
        )

    return generated_env, generated_s0


def get_problem_for_goal(
    domain: FullDomain, planning_representation, goal, base_env=None
):
    # Only need to generate_unsatisfying_consistent_world for a universally quantified world
    if isinstance(goal, ImproperQuantifiedSet):
        if goal.quantifier == "forall":
            generated_env, generated_s0 = generate_unsatisfying_consistent_world(
                domain, base_env, planning_representation, goal
            )
        elif goal.quantifier == "exists":
            # For an existential quantifier, we need to generate at least
            # enough to bind the goal to *something*, but we can't know if we
            # have generated far enough until we find a plan
            generated_env, generated_s0 = generate_bindable_world(
                domain, base_env, planning_representation, goal
            )
        else:
            raise Exception(f"Unknown quantifier type {goal.quantifier}")
    else:
        # If we don't have to worry about quantifiers, we just need to set up
        # some variables to support applying domain rules
        generated_s0 = copy.deepcopy(planning_representation)
        generated_symbols = get_symbols_from_facts(planning_representation.facts)
        symbol_to_type = get_symbol_to_type(domain.pddl_domain, planning_representation)
        generated_env = Environment(base_env, generated_symbols, symbol_to_type)

    generated_s0 = apply_rules(domain.derived_stream_facts, generated_env, generated_s0)
    if isinstance(goal, ImproperQuantifiedSet):
        evaled_goal = eval_quantifier(generated_env, goal, generated_s0.facts)
    else:
        evaled_goal = goal

    return generated_env, Problem(generated_s0, evaled_goal)
