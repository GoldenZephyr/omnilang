from testing import forall, Fact, Environment, generate, Symbol, State
from dsg_pddl.pddl_grounding import PddlDomain
from streams import (
    Stream,
    find_streams_affecting_goal,
    expand_streams,
    eval_quantifier,
    get_symbols_from_facts,
    get_symbol_to_type,
)
from solver import solve
import copy


def apply_transitive_frontier_rule(facts):
    connected_facts = [f for f in facts if f.head == "connected"]
    print("connected facts: ", connected_facts)
    frontiers = [f.body[0] for f in facts if f.head == "frontier"]
    print("frontiers: ", frontiers)

    def frontier_other_from_connected(fact):
        arg1_frontier = fact.body[0] in frontiers
        arg2_frontier = fact.body[1] in frontiers
        if arg1_frontier:
            if arg2_frontier:
                return None, None
            return fact.body[0], fact.body[1]
        if arg2_frontier:
            return fact.body[1], fact.body[0]
        return None, None

    for c1 in connected_facts:
        f1, o1 = frontier_other_from_connected(c1)
        for c2 in connected_facts:
            f2, o2 = frontier_other_from_connected(c2)
            if f1 == f2 and o1 != o2:
                new_connection = Fact("connected", [o1, o2])
                facts.append(new_connection)


def apply_rules(facts):
    # want to apply rule e.g. (connected p1 f1) (connected f1 p2) -> (connected p1 p2)
    # TODO: generalize...
    apply_transitive_frontier_rule(facts)


goal = forall("p", "place", Fact("visited", [Symbol("p")]))

stream1 = Stream(
    "dummy-stream",
    [Symbol("?g")],
    [Fact("DNE", [Symbol("?g")])],
    ["?widget"],
    [
        Fact("shoe", [Symbol("?widget")]),
        Fact("on", [Symbol("?g"), Symbol("?shoe")]),
    ],
    symbol_prefixes=["dummy"],
)

stream2 = Stream(
    "generate-frontiers",
    [Symbol("?f")],
    [Fact("frontier", [Symbol("?f")])],
    ["?place"],
    [
        Fact("place", [Symbol("?place")]),
        Fact("connected", [Symbol("?f"), Symbol("?place")]),
    ],
    symbol_prefixes=["pred"],
)

# This stream doesn't really do anything meaningful but is for testing dependencies
stream3 = Stream(
    "dummy-frontier-generator",
    [Symbol("?o")],
    [Fact("object", [Symbol("?o")])],
    ["?f"],
    [
        Fact("frontier", [Symbol("?f")]),
        Fact("connected", [Symbol("?o"), Symbol("?f")]),
    ],
    symbol_prefixes=["pred-frontier"],
)

# original_symbols = [Symbol("f1"), Symbol("f2"), Symbol("o1"), Symbol("p1")]
facts = [
    Fact("frontier", [Symbol("f1")]),
    Fact("frontier", [Symbol("f2")]),
    Fact("place", [Symbol("p1")]),
    Fact("obj", [Symbol("o1")]),
    Fact("connected", [Symbol("f1"), Symbol("p1")]),
    Fact("connected", [Symbol("f2"), Symbol("p1")]),
    Fact("at", [Symbol("p1")]),
    Fact("visited", [Symbol("p1")]),
]
s0 = State(facts)

affecting_streams_1 = find_streams_affecting_goal([stream1], s0, goal)
affecting_streams_2 = find_streams_affecting_goal([stream1, stream2], s0, goal)
affecting_streams_3 = find_streams_affecting_goal([stream1, stream2, stream3], s0, goal)

new_state = expand_streams(None, affecting_streams_3, s0)
print("new state: ", new_state)

relevant_streams = affecting_streams_2

generated_s0 = copy.deepcopy(s0)
generated_symbols = get_symbols_from_facts(s0.facts)
symbol_to_type = get_symbol_to_type(None, s0)
generated_env = Environment(None, generated_symbols, symbol_to_type)

# Expand state until the goal is no longer true in the initial state
max_depth = 10
for depth in range(max_depth):
    # restrict goal, check if goal in s0
    evaled_goal = eval_quantifier(generated_env, goal, generated_s0)
    explicit_goal = [g for g in generate(evaled_goal)]
    if explicit_goal not in s0:
        break
    generated_env, generated_s0 = expand_streams(
        generated_env, relevant_streams, generated_s0
    )

print("Generated initial state: ")
for s in generated_s0.facts:
    print(s)

print("Generated env: ", generated_env)

apply_rules(generated_s0.facts)
print("Initial state after applied rules")
for s in generated_s0.facts:
    print(s)

evaled_goal = eval_quantifier(generated_env, goal, generated_s0.facts)

with open("test_domain.pddl", "r") as fo:
    domain = PddlDomain(fo.read())
plan = solve(domain, generated_s0, evaled_goal)

# tuple_goal = ("and",) + tuple(a.to_tuple() for a in generate(evaled_goal))
#
# objects = group_objects_by_type(None, generated_s0.facts)  # TODO: pass through domain
# problem = PddlProblem(
#    name="test_explore",
#    domain="exploration_test",
#    # TODO: "T" is temporary until we properly deal with types vs unary predicates
#    objects={k + "T": [o.identifier for o in objs] for k, objs in objects.items()},
#    initial_facts=[i.to_tuple() for i in generated_s0.facts],
#    goal=tuple_goal,
#    optimizing=False,
# )
#
# problem_string = problem.to_string()
#
# grounded_problem = GroundedPddlProblem(domain, problem_string, {})
# plan = solve_pddl(grounded_problem)
print(plan)

# plan = forward_search([move_visited], generated_env, generated_s0, test_goal)
# print("Plan: ", plan)
