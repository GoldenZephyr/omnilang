import spark_dsg
import numpy as np
from omnilang.testing_scene_graphs import (
    build_NxN_dsg,
    add_object_to_place,  # noqa
    label_region,
    layer_to_name,
    plot_generated_env,
    plot_dsg,
    plot_state,
    add_grid_regions,
)
from dsg_exploration_sim.plotting import (
    plot_plan_in_env,
)
import omnilang as oml
from dsg_exploration_sim.simulator import add_frontiers
from dsg_exploration_sim.derived_dsg import DerivedDsg
import matplotlib.pyplot as plt
from dsg_exploration_sim.action_and_states import SimulationState
from pddl_factor_graph.pddl_factors import UninitializedValue, PddlFactor
from pddl_factor_graph.pddl_factor_graph_solver import resolve_uninitialized_variables

from search_manager import BspManager

import sys


def get_env_and_state(Gobs, sim_state, domain, all_places_observed):
    type_to_subtypes = oml.compute_descendant_types(domain.pddl_domain.types)
    symbol_to_type, pddl_s0 = oml.dsg_to_region_problem(
        Gobs,
        spark_dsg.NodeSymbol(sim_state.current_node).str(),
        special_object_categories=type_to_subtypes.get("obj", []),
    )
    oml.augment_planning_representation(
        DerivedDsg(Gobs), sim_state, pddl_s0, all_places_observed=all_places_observed
    )

    dsg_env = oml.DsgEnvironment(Gobs)
    env = oml.Environment(dsg_env, [], symbol_to_type, domain.pddl_domain.types)
    return env, pddl_s0


def plot_solution(G, Gobs, sim_state, new_env, new_facts, plan):
    labels_for_legend = {}
    # labels_for_legend |= plot_dsg(G, 0.4)
    # labels_for_legend = layer_to_name(G, labels_for_legend, new_prefix="gt-")

    obs_labels = plot_dsg(Gobs, plot_labels=False)
    obs_labels = layer_to_name(Gobs, obs_labels)
    labels_for_legend |= obs_labels

    plot_state(Gobs, sim_state)
    # plan_labels = plot_plan_in_env(new_env, Gobs, plan)
    # labels_for_legend |= plan_labels

    gen_label_to_line = plot_generated_env(
        new_env, new_facts, {"food": ">", "place": "p", "cone": "^"}, plot_labels=False
    )
    labels_for_legend |= gen_label_to_line
    lines = labels_for_legend.values()
    labels = labels_for_legend.keys()
    # plt.legend(lines, labels)


def setup_dsg():
    G = build_NxN_dsg(9, 9)
    add_grid_regions(G, -0.5, 3)

    label_region(G, "parking", "r6")
    label_region(G, "parking", "r7")
    label_region(G, "intersection", "r1")

    # add_object_to_place(G, "box", 1, spark_dsg.NodeSymbol("t", 8))
    add_object_to_place(G, "cone", 1, spark_dsg.NodeSymbol("t", 55))  # cone in r6

    # Partial Exploration
    observed_place_idx = [0, 1, 2, 3, 9, 10, 11, 12, 18, 19, 20, 21, 27, 28, 29, 30]
    # observed_region_idx = [0, 1, 3, 4]
    observed_object_idx = []

    # Full Exploration
    # observed_place_idx = list(range(81))
    known_region_idx = list(range(9))

    full_place_observation = False
    if full_place_observation:
        observed_place_vals = set(
            n.id.value for n in G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY).nodes
        )
    else:
        observed_place_vals = set(
            spark_dsg.NodeSymbol("t", idx).value for idx in observed_place_idx
        )

    observed_object_vals = set(
        spark_dsg.NodeSymbol("o", idx).value for idx in observed_object_idx
    )
    known_region_vals = set(
        spark_dsg.NodeSymbol("r", idx).value for idx in known_region_idx
    )

    observed_vals = observed_place_vals | observed_object_vals | known_region_vals
    Gobs = G.create_subgraph(observed_vals)
    Gobs.metadata.add(dict(G.metadata.get()))
    add_frontiers(G, DerivedDsg(Gobs))

    initial_node = spark_dsg.NodeSymbol("t", 0)
    # observed_place_vals_for_planning = observed_place_vals
    observed_place_vals_for_planning = set()
    sim_state = SimulationState(
        initial_node.value, set(), observed_place_vals_for_planning
    )

    return G, Gobs, sim_state


def dummy_position_offset(node):
    if "position" in node and node["position"] is not None:
        pos = node["position"] + np.array([0.1, 0, 0])
    else:
        pos = None
    return [{"position": pos}]


def placeholder_position_generator(node):
    parent_position = node.get("position", None)
    if isinstance(parent_position, np.ndarray) or isinstance(parent_position, list):
        initial_guess = node["position"]
    else:
        initial_guess = None

    var = UninitializedValue(3, initial_guess)
    return [{"position": var}]


def setup_domain(Gobs, sim_state):
    stream_paths = ["../streams/place_beyond_frontier.pddl"]
    unknown_places = True
    enable_objects = True
    if unknown_places:
        stream_paths.append("../streams/region_streams.pddl")
    if enable_objects:
        # stream_paths.append("../streams/simple_place_generates_food.pddl")
        stream_paths.append("../streams/smart_pick_streams.pddl")
        stream_paths.append("../streams/cone_stream.pddl")

    pddl_path = "../domains/grid_region_domain.pddl"

    stream_functions = {}
    stream_functions["frontier-generates-place"] = placeholder_position_generator
    stream_functions["region-generates-place"] = placeholder_position_generator
    # stream_functions["unobserved-place-generates-food"] = placeholder_position_generator
    stream_functions["generate-possible-object"] = placeholder_position_generator
    domain = oml.load_full_domain(pddl_path, stream_paths, stream_functions)

    env, pddl_s0 = get_env_and_state(
        Gobs, sim_state, domain, all_places_observed=unknown_places
    )

    def construct_bsp(goal):
        problem = oml.Problem(pddl_s0, goal)
        bpm = BspManager(domain, env, problem, n_models=200)
        return bpm

    return construct_bsp


def near_factor(s: dict, t: dict, expected_distance=1):
    return expected_distance - np.linalg.norm(s["position"] - t["position"])
    # return np.linalg.norm(s["position"] - t["position"])
    # return s["position"] - t["position"]


if __name__ == "__main__":
    G, Gobs, sim_state = setup_dsg()

    # plot_dsg(Gobs, plot_labels=False)
    # # plot_dsg(G, plot_labels=False)
    # plt.show()
    # abc

    valid_goals = [
        "goto-region",
        "search-region",
        "get-cone",
    ]
    if len(sys.argv) < 2:
        print("Usage: python gridworld.py <example name>")
        exit(1)
    goaltype = sys.argv[1]

    match goaltype:
        case "goto-region":
            target_region = "r8"
            # goal = oml.PartialState(
            #    {oml.Fact("in-region", [oml.Symbol(target_region)])}, set()
            # )
            goal = oml.Fact("in-region", [oml.Symbol(target_region)])
            goal_str = f"Goto region {target_region}"
            domain_constructor = setup_domain
        case "search-region":
            target_region = "r6"

            # NOTE: Ideally we would use this goal, although we don't directly
            # support goals like this yet. Currently observed-region needs to
            # manually be implemented as a derived stream, but ideally we
            # automatically translate this goal into that derived stream form.
            # goal = str_to_goal(
            #     "(forall (?p - place) (implies (place-in-region ?p {target_region}) (observed ?p)))"
            # )
            # goal = oml.PartialState(
            #    {oml.Fact("searched-region", [oml.Symbol(target_region)])}, set()
            # )
            goal = oml.Fact("searched-region", [oml.Symbol(target_region)])
            goal_str = f"Search {target_region}"
            domain_constructor = setup_domain
        case "get-cone":
            goal = oml.ExistentialQuantifier(
                [oml.Symbol("?c")],
                ["cone"],
                oml.Fact("holding", [oml.Symbol("?c")]),
                # oml.Fact("obj-at", [oml.Symbol("?c"), oml.Symbol("t0")]),
            )

            goal_str = "Grab Cone"
            domain_constructor = setup_domain
        case "block-intersections":
            goal = oml.UniversalQuantifier(
                [oml.Symbol("?r")],
                ["intersection"],
                oml.ExistentialQuantifier(
                    [oml.Symbol("?c")],
                    ["cone"],
                    oml.Fact("object-in-region", [oml.Symbol("?c"), oml.Symbol("?r")]),
                ),
            )

            # goal = oml.ExistentialQuantifier(
            #     [oml.Symbol("?c")],
            #     ["cone"],
            #     oml.Fact("object-in-region", [oml.Symbol("?c"), oml.Symbol("r1")]),
            # )

            # goal = oml.Conjunction(
            #     [
            #         oml.ExistentialQuantifier(
            #             [oml.Symbol("?c")],
            #             ["cone"],
            #             oml.Fact("holding", [oml.Symbol("?c")]),
            #         ),
            #         oml.Fact("in-region", [oml.Symbol("r1")]),
            #     ],
            # )

            goal_str = "Block all intersections"
            domain_constructor = setup_domain

        case _:
            print(f"Please use a goal in {valid_goals}")
            exit(1)

    predicate_to_factor = {}
    predicate_to_factor["place-in-region"] = PddlFactor(near_factor, 1, 5.0)
    predicate_to_factor["connected"] = PddlFactor(near_factor, 1, 1.0)
    predicate_to_factor["obj-at"] = PddlFactor(near_factor, 1, 1.0)

    bpm = domain_constructor(Gobs, sim_state)(goal)

    # solutions = bpm.search((2, 6), (12, 14), take_first_plan=True)
    managers, generators, solutions = bpm.search((4, 6), (12, 16), take_first_plan=True)
    # solutions = bpm.search((2, 6), (32, 35), take_first_plan=True)
    # solutions = bpm.search((0, 6), (1, 20))
    # new_env, new_facts, plan = bpm.search_at_level(1, 4)

    for key, s in solutions.items():
        new_env, new_facts, plan = s
        for f in new_facts.facts:
            print(f)
        resolve_uninitialized_variables(new_env, new_facts, predicate_to_factor)
        print("plan: ", plan)
        plot_solution(G, Gobs, sim_state, new_env, new_facts, plan)
        level, horizon = key
        plt.title(f"{goal_str} - Level {level}, Horizon {horizon}")
        plt.show()
