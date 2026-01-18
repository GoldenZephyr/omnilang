from omnilang.mdp_states import forall, Fact, Environment, generate, Symbol, State
from dsg_pddl.pddl_grounding import PddlDomain
from streams import (
    find_streams_affecting_goal,
    expand_streams,
    eval_quantifier,
    get_symbols_from_facts,
    get_symbol_to_type,
)
from solver import solve
import copy
from parse_streams import parse_stream_file

from rules import apply_rules

goal = forall("p", "place", Fact("visited", [Symbol("p")]))

streams = parse_stream_file("streams.pddl")
stream1 = streams[0]
stream2 = streams[1]
stream3 = streams[2]

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
    #if explicit_goal not in s0:
    if explicit_goal not in generated_s0:
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
print(plan)
