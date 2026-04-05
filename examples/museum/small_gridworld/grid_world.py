import spark_dsg
import numpy as np
from omnilang.testing_scene_graphs import (
    build_NxN_dsg,
    add_object_to_place,
    layer_to_name,
    plot_generated_env,
    plot_dsg,
    plot_state,
)
from dsg_exploration_sim.plotting import (
    plot_plan_in_env,
)
import omnilang as oml
from dsg_exploration_sim.simulator import add_frontiers
from dsg_exploration_sim.derived_dsg import DerivedDsg
import matplotlib.pyplot as plt
from dsg_exploration_sim.action_and_states import SimulationState


import sys


def get_env_and_state(Gobs, sim_state, domain):
    symbol_to_type, pddl_s0 = oml.dsg_to_problem(
        Gobs,
        spark_dsg.NodeSymbol(sim_state.current_node).str(),
        special_object_categories=["food", "box"],
        include_object_connections=True,
    )
    oml.augment_planning_representation(DerivedDsg(Gobs), sim_state, pddl_s0)

    dsg_env = oml.DsgEnvironment(Gobs)
    env = oml.Environment(dsg_env, [], symbol_to_type, domain.pddl_domain.types)
    return env, pddl_s0


def plot_solution(G, Gobs, sim_state, new_env, plan):
    labels_for_legend = plot_dsg(G, 0.4)
    labels_for_legend = layer_to_name(G, labels_for_legend, new_prefix="gt-")
    obs_labels = plot_dsg(Gobs)
    obs_labels = layer_to_name(Gobs, obs_labels)
    labels_for_legend |= obs_labels
    plot_state(Gobs, sim_state)
    plan_labels = plot_plan_in_env(new_env, Gobs, plan)
    labels_for_legend |= plan_labels
    gen_label_to_line = plot_generated_env(new_env, {"food": ">", "place": "p"})
    labels_for_legend |= gen_label_to_line
    lines = labels_for_legend.values()
    labels = labels_for_legend.keys()
    plt.legend(lines, labels)


def setup_dsg():
    G = build_NxN_dsg(3, 3)

    add_object_to_place(G, "box", 1, spark_dsg.NodeSymbol("t", 8))
    add_object_to_place(G, "box", 2, spark_dsg.NodeSymbol("t", 1))

    observed_place_idx = [0, 1, 3, 4]
    observed_object_idx = [2]

    observed_place_vals = set(
        spark_dsg.NodeSymbol("t", idx).value for idx in observed_place_idx
    )
    observed_object_vals = set(
        spark_dsg.NodeSymbol("o", idx).value for idx in observed_object_idx
    )

    observed_vals = observed_place_vals | observed_object_vals
    Gobs = G.create_subgraph(observed_vals)
    Gobs.metadata.add(dict(G.metadata.get()))
    add_frontiers(G, DerivedDsg(Gobs))

    initial_node = spark_dsg.NodeSymbol("t", 0)
    sim_state = SimulationState(initial_node.value, set(), observed_place_vals)

    return G, Gobs, sim_state


def dummy_position_offset(node):
    return [{"position": node["position"] + np.array([0.1, 0, 0])}]


def setup_domain_simple(Gobs, sim_state):
    stream_path = [
        "../streams/place_beyond_frontier.pddl",
        "../streams/simple_place_generates_food.pddl",
    ]
    pddl_path = "../domains/myopic_pick.pddl"

    stream_functions = {}
    stream_functions["frontier-generates-place"] = dummy_position_offset
    stream_functions["unobserved-place-generates-food"] = dummy_position_offset
    domain = oml.load_full_domain(pddl_path, stream_path, stream_functions)

    env, pddl_s0 = get_env_and_state(Gobs, sim_state, domain)

    def construct_bsp(goal):
        problem = oml.Problem(pddl_s0, goal)
        bpm = oml.BspManager(domain, env, problem)
        return bpm

    return construct_bsp


def setup_domain_observeall(Gobs, sim_state):
    stream_path = [
        "../streams/place_beyond_frontier.pddl",
        "../streams/simple_place_generates_food.pddl",
    ]
    pddl_path = "../domains/observeall_domain.pddl"

    stream_functions = {}
    stream_functions["frontier-generates-place"] = dummy_position_offset
    stream_functions["unobserved-place-generates-food"] = dummy_position_offset
    domain = oml.load_full_domain(pddl_path, stream_path, stream_functions)

    env, pddl_s0 = get_env_and_state(Gobs, sim_state, domain)

    def construct_bsp(goal):
        problem = oml.Problem(pddl_s0, goal)
        bpm = oml.BspManager(domain, env, problem)
        return bpm

    return construct_bsp


def setup_domain_modal_pick(Gobs, sim_state):
    stream_path = [
        "../streams/place_beyond_frontier.pddl",
        "../streams/smart_pick_streams.pddl",
    ]
    pddl_path = "../domains/smart_pick.pddl"

    stream_functions = {}
    stream_functions["frontier-generates-place"] = dummy_position_offset
    stream_functions["unobserved-place-generates-food"] = dummy_position_offset
    domain = oml.load_full_domain(pddl_path, stream_path, stream_functions)

    env, pddl_s0 = get_env_and_state(Gobs, sim_state, domain)

    def construct_bsp(goal):
        problem = oml.Problem(pddl_s0, goal)
        bpm = oml.BspManager(domain, env, problem)
        return bpm

    return construct_bsp


if __name__ == "__main__":
    G, Gobs, sim_state = setup_dsg()

    valid_goals = [
        "observeall",
        "goto",
        "pickup",
        "getobj",
        "getobj-easy",
        "observeall-group",
    ]
    if len(sys.argv) < 2:
        print("Usage: python gridworld.py <example name>")
        exit(1)
    goaltype = sys.argv[1]

    match goaltype:
        case "observeall":
            goal = oml.PddlForall(
                [oml.Symbol("?p")], ["place"], oml.Fact("observed", [oml.Symbol("?p")])
            )
            goal_str = "Observe all places"
            domain_constructor = setup_domain_simple
        case "goto":
            goal = oml.PartialState({oml.Fact("at", [oml.Symbol("t4")])}, set())
            goal_str = "Goto t4"
            domain_constructor = setup_domain_simple
        case "pickup":
            goal = oml.PddlExists(
                [oml.Symbol("?f")],
                ["food"],
                oml.Fact("holding", [oml.Symbol("?f")]),
            )
            goal_str = "Pick up food"
            domain_constructor = setup_domain_simple
        case "getobj":
            goal = oml.PddlExists(
                [oml.Symbol("?f")],
                ["food"],
                oml.Fact("obj-at", [oml.Symbol("?f"), oml.Symbol("t0")]),
            )
            goal_str = "Bring food to origin"
            domain_constructor = setup_domain_simple
        case "getobj-easy":
            # Lifted Version
            goal = oml.PddlExists(
                [oml.Symbol("?b")],
                ["box"],
                oml.Fact("obj-at", [oml.Symbol("?b"), oml.Symbol("t3")]),
            )
            # Grounded Version
            # goal = oml.PartialState(
            #    {oml.Fact("obj-at", [oml.Symbol("O2"), oml.Symbol("t3")])}, set()
            # )
            goal_str = "Bring box to t3"
            domain_constructor = setup_domain_simple
        case "observeall-group":
            goal = oml.PddlForall(
                [oml.Symbol("?p")], ["place"], oml.Fact("observed", [oml.Symbol("?p")])
            )
            goal_str = "Observe all places (group action)"
            domain_constructor = setup_domain_observeall
        case "getobj-smart":
            goal = oml.PddlExists(
                [oml.Symbol("?f")],
                ["food"],
                # oml.Fact("holding", [oml.Symbol("?f")]),
                oml.Fact("obj-at", [oml.Symbol("?f"), oml.Symbol("t0")]),
            )
            goal_str = "Bring food to origin (but smarter)"
            # goal = oml.PddlForall(
            #    [oml.Symbol("?p")], ["place"], oml.Fact("observed", [oml.Symbol("?p")])
            # )

            domain_constructor = setup_domain_modal_pick

        case _:
            print(f"Please use a goal in {valid_goals}")
            exit(1)

    bpm = domain_constructor(Gobs, sim_state)(goal)

    solutions = bpm.search((0, 5), (1, 9))
    # solutions = bpm.search((0, 6), (1, 20))
    # new_env, new_facts, plan = bpm.search_at_level(1, 4)

    for key, s in solutions.items():
        new_env, new_facts, plan = s
        print("plan: ", plan)
        plot_solution(G, Gobs, sim_state, new_env, plan)
        level, horizon = key
        plt.title(f"{goal_str} - Level {level}, Horizon {horizon}")
        plt.show()
