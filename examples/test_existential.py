from omnilang.mdp_states import (
    exists,
    Fact,
    Symbol,
    # push,
    restrict,
    Environment,
    generate,
    PartialState,
    ImproperQuantifiedSet,
)
from omnilang.graph_builder import build_test_dsg
from omnilang.test_planner import (
    dsg_to_problem,
    load_full_domain,
    get_problem_for_goal,
    FullDomain,
)
from omnilang.solver import solve
from omnilang.rules import apply_rules
from omnilang.streams import (
    expand_streams,
    get_symbols_from_facts,
    get_symbol_to_type,
    find_streams_affecting_goal,
    eval_quantifier,
)
import copy
import math  # noqa


def solve_problem_for_existential_goal(
    domain: FullDomain, planning_representation, goal, base_env=None
):
    # TODO: Also need to try planning before expanding *any* streams
    relevant_streams = find_streams_affecting_goal(
        domain.streams, planning_representation, goal
    )

    generated_s0 = copy.deepcopy(planning_representation)
    generated_symbols = get_symbols_from_facts(planning_representation.facts)
    symbol_to_type = get_symbol_to_type(None, planning_representation)
    generated_env = Environment(base_env, generated_symbols, symbol_to_type)

    max_depth = 10
    # stream_evals_per_level = math.inf
    stream_evals_per_level = 1
    for depth in range(max_depth):
        # restrict goal, check if goal in s0
        if isinstance(goal, ImproperQuantifiedSet):
            evaled_goal = eval_quantifier(generated_env, goal, generated_s0)
            explicit_goal = [g for g in generate(evaled_goal)]
            print("explicit goal: ", explicit_goal)
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

        current_s0 = copy.deepcopy(generated_s0)

        apply_rules(current_s0.facts)
        if isinstance(goal, ImproperQuantifiedSet):
            evaled_goal = eval_quantifier(generated_env, goal, current_s0.facts)
        else:
            evaled_goal = goal

        print("\n\nevaled goal: ", evaled_goal)
        plan = solve(domain.pddl_domain, current_s0, evaled_goal)
        print("Plan: ", plan)
        if plan is not None:
            break

    return generated_env, plan


goal = exists("p", "Place", Fact("visited", [Symbol("p")]))

# print(push(goal))

env_symbols = [Symbol("p1"), Symbol("p2"), Symbol("p3")]
env_symbol_to_type = {}
env_symbol_to_type["p1"] = "Place"
env_symbol_to_type["p2"] = "Place"
env_symbol_to_type["p3"] = "Place"

goal = restrict(
    Environment(None, env_symbols, env_symbol_to_type), goal, "p", ["p1", "p2", "p3"]
)


for gs in generate(goal):
    print(gs)


goal = exists("c", "food", Fact("obj-at", [Symbol("c"), Symbol("t0")]))

G = build_test_dsg()
planning_representation = dsg_to_problem(G, "t0", include_object_connections=True)

# plot_layer(G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY))
# plot_frontiers(G)
# plt.show()

stream_path = "streams.pddl"
pddl_domain_path = "pick_domain.pddl"
domain = load_full_domain(pddl_domain_path, stream_path)

planning_representation.add_fact(Fact("observed", [Symbol("t0")]))
planning_representation.add_fact(Fact("hand-free", []))

s0 = copy.deepcopy(planning_representation)
generated_symbols = get_symbols_from_facts(planning_representation.facts)
symbol_to_type = get_symbol_to_type(None, planning_representation)
env = Environment(None, generated_symbols, symbol_to_type)

relevant_streams = domain.streams
new_env, new_s0 = expand_streams(env, relevant_streams, s0, stream_evals_per_level=1)

generated_env, plan = solve_problem_for_existential_goal(
    domain, planning_representation, goal, env
)

abc

goal = exists("p", "place", Fact("visited", [Symbol("p")]))

# planning_representation.facts.append(Fact("visited", [Symbol("t1")]))

print("initial state: ", planning_representation)


env, problem = get_problem_for_goal(domain, planning_representation, goal)

plan = solve(domain.pddl_domain, problem.initial_state, problem.goal)

abc

domain = load_full_domain("pick_domain.pddl", stream_path)
rep = dsg_to_problem(G, "t0", include_object_connections=True)
rep.facts.append(Fact("hand-free", []))
goal = PartialState({Fact("obj-at", [Symbol("o1"), Symbol("t0")])}, set())
env, problem = get_problem_for_goal(domain, rep, goal)
plan = solve(domain.pddl_domain, problem.initial_state, problem.goal)
