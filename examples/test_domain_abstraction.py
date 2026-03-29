import omnilang as oml
from clingo_stream_planning import (
    group_action_to_clingo,
    solve_clingo_problem,
    pddl_problem_to_state,
)
import numpy as np


def frontier_generates_place(frontier_data):
    return [{"position": frontier_data["position"] + np.array([0.1, 0, 0])}]


domain = oml.parse_domain_file("domain_abstraction.pddl")


clg = group_action_to_clingo(domain.group_actions[0])

for line in clg:
    print(line)

stream_path = "reachable_streams.pddl"
pddl_path = "domain_abstraction.pddl"
problem_path = "test_problem.pddl"

stream_functions = {}
stream_functions["frontier-generates-place"] = frontier_generates_place
domain = oml.load_full_domain(pddl_path, stream_path, stream_functions)

problem = oml.parse_problem_file(problem_path)
og_problem = problem
s0, env = pddl_problem_to_state(problem)

env = oml.Environment(env, [oml.Symbol("group1")], {"group1": "object"})
env.attach_metadata(oml.Symbol("group1"), {"group_type": "place"})

env.attach_metadata(oml.Symbol("f1"), {"position": np.array([0, 0, 1])})
env.attach_metadata(oml.Symbol("f2"), {"position": np.array([0, 0, 1])})

s0 = oml.State(s0.facts | set([oml.Fact("group", [oml.Symbol("group1")])]))


goal = problem.goal

if isinstance(goal, oml.PddlForall):
    forall_goal = oml.forall(
        goal.unbound_elements[0].identifier, goal.type_restrictions[0], goal.body
    )
    generated_env, generated_s0 = oml.generate_unsatisfying_consistent_world(
        domain, env, s0, forall_goal
    )
elif isinstance(goal, oml.PddlExists):
    exists_goal = oml.exists(
        goal.unbound_elements[0].identifier, goal.type_restrictions[0], goal.body
    )
    generated_env, generated_s0 = oml.generate_bindable_world(
        domain, env, s0, exists_goal
    )
else:
    generated_env = env
    generated_s0 = s0


# problem = oml.Problem(s0, problem.goal)
# manager = solve_clingo_problem(domain, env, problem, max_horizon=8)

problem = oml.Problem(s0, problem.goal)
manager = solve_clingo_problem(domain, generated_env, problem, max_horizon=2)

if manager is None:
    print("No plan found")

print(manager.get_next_plan())
print(manager.get_groupings())
new_env, new_facts, plan = manager.get_next_plan_and_world(env, generated_env, domain)
