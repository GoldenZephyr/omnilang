from omnilang.mdp_states import (
    forall,
    Fact,
    Symbol,
    push,
    restrict,
    Environment,
    generate,
    State,
    PartialState,
)

from omnilang.mdp_actions import LiftedAction, ground_actions
from omnilang.mdp_search import iterate_neighbors, forward_search

goal = forall("p", "Place", Fact("visited", Symbol("p")))

print(push(goal))

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


move = LiftedAction(
    "move",
    ["?p1", "?p2"],
    [[], []],
    [Fact("at", ["?p1"])],
    [Fact("at", ["?p2"])],
    [Fact("at", ["?p1"])],
)

actions = [move]
symbols = ["p1", "p2"]
for a in ground_actions(actions, symbols):
    print(a)


s0 = State(
    [
        Fact("at", [Symbol("p1")]),
        Fact("connected", [Symbol("p1"), Symbol("p2")]),
        Fact("connected", [Symbol("p2"), Symbol("p3")]),
    ]
)
print("Possible s1: ")
for a, n in iterate_neighbors(actions, env_symbols, s0):
    print("Action: ", a, " Next state: ", n)


move_real = LiftedAction(
    "move",
    ["?p1", "?p2"],
    [[], []],
    [Fact("at", ["?p1"]), Fact("connected", ["?p1", "?p2"])],
    [Fact("at", ["?p2"])],
    [Fact("at", ["?p1"])],
)

test_goal = PartialState({Fact("at", [Symbol("p3")])}, {})
plan = forward_search([move_real], env_symbols, s0, test_goal)
print("Plan: ", plan)


# 1. forward search -- DONE
# 2. action inversion
#    * In general an action has ~2^N inverses where N is the number of action effects. (every effect can be inverted or left unchanged)
# 3. "goal state" check is true when the search state matches the problem's intial state, *or a "pure abstraction" of the initial state*

print("Move real: ")
print(move_real)


from parse_mdp import parse_domain_file
domain = parse_domain_file("move_action_test.pddl")
print("Loaded move: ")
print(domain.actions)
