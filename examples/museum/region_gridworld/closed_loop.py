from omnilang.testing_scene_graphs import (
    add_object_to_place,  # noqa
)
import omnilang as oml
import matplotlib.pyplot as plt
from pddl_factor_graph.pddl_factors import PddlFactor
from pddl_factor_graph.pddl_factor_graph_solver import resolve_uninitialized_variables

from region_grid_world import setup_dsg, setup_domain, near_factor, plot_solution
from dsg_exploration_sim.westpoint_pddl_bridge import sim_transformer_wp
from dsg_exploration_sim.simulator import (
    add_frontiers,
    compute_updated_dsg,
    apply_update,
)


import sys

if __name__ == "__main__":
    G, Gobs, sim_state = setup_dsg()

    valid_goals = [
        "goto-region",
        "search-region",
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
        case _:
            print(f"Please use a goal in {valid_goals}")
            exit(1)

    predicate_to_factor = {}
    predicate_to_factor["place-in-region"] = PddlFactor(near_factor, 1, 5.0)
    predicate_to_factor["connected"] = PddlFactor(near_factor, 1, 1.0)
    predicate_to_factor["obj-at"] = PddlFactor(near_factor, 1, 1.0)

    current_state = sim_state
    Gobs = None

    for idx in range(10):
        position = G.get_node(current_state.current_node).attributes.position
        Gobs = compute_updated_dsg(G, Gobs, position, 4)
        # plot_dsg(Gobs.base_dsg)
        # plt.show()
        add_frontiers(G, Gobs)
        bpm = domain_constructor(Gobs.base_dsg, sim_state)(goal)

        solutions = bpm.search((5, 6), (1, 10), take_first_plan=True)
        # solutions = bpm.search((0, 6), (1, 20))
        # new_env, new_facts, plan = bpm.search_at_level(1, 4)

        for key, s in solutions.items():
            new_env, new_facts, plan = s
            for f in new_facts.facts:
                print(f)
            resolve_uninitialized_variables(new_env, new_facts, predicate_to_factor)
            print("plan: ", plan)
            _, compiled_plan = sim_transformer_wp.transform(new_env, plan)
            print("Compiled plan: ", compiled_plan)
            plot_solution(G, Gobs.base_dsg, sim_state, new_env, new_facts, plan)
            level, horizon = key
            plt.title(f"{goal_str} - Level {level}, Horizon {horizon}")
            plt.show()
            break
        action = compiled_plan[0]
        apply_update(current_state, G, action)
