# ruff: noqa: F811
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
    ground_predicate,
)

from omnilang.mdp_actions import LiftedAction, ground_actions, GroundedAction
from omnilang.mdp_search import iterate_neighbors, forward_search
from parse_mdp import parse_domain_file
from omnilang.test_planner import load_full_domain, get_problem_for_goal
from omnilang.solver import solve


def can_produce(env: Environment, action: LiftedAction, fact: Fact) -> bool:
    # TODO: this can be made more efficient by ensuring that the symbol types match
    for f in action.positive_effect:
        if f.head == fact.head:
            return True


def partially_ground_by_output(action: LiftedAction, fact: Fact) -> LiftedAction:
    for f in action.positive_effect:
        if f.head == fact.head:
            if len(f.body) != len(fact.body):
                raise ValueError(
                    f"Currently don't support variadic facts. Found {f} vs {fact}"
                )
        fact_to_bind = f
        # TODO: handle multiple potential bindings?
        break

    grounded_formal_param = {s for s in fact_to_bind.body}
    formal_to_updated = {s: g for s, g in zip(fact_to_bind.body, fact.body)}
    for s in action.params:
        if s not in grounded_formal_param:
            formal_to_updated[Symbol(s)] = Symbol(s)

    new_action_symbols = []
    new_restrictions = []
    for s, r in zip(action.params, action.param_restrictions):
        if s not in grounded_formal_param:
            new_action_symbols.append(s)
            new_restrictions.append(r)

    grounded_precondition = []
    for p in action.precondition:
        grounded_precondition.append(ground_predicate(p, formal_to_updated))

    grounded_positive_effects = [
        ground_predicate(p, formal_to_updated) for p in action.positive_effect
    ]
    grounded_negative_effects = [
        ground_predicate(p, formal_to_updated) for p in action.negative_effect
    ]

    if len(new_action_symbols) == 0:
        return GroundedAction(
            action.name,
            grounded_precondition,
            grounded_positive_effects,
            grounded_negative_effects,
        )
    else:
        return LiftedAction(
            action.name,
            new_action_symbols,
            new_restrictions,
            grounded_precondition,
            grounded_positive_effects,
            grounded_negative_effects,
        )


def get_env_symbols(env: Environment):
    if env.parent_environment is not None:
        parent_symbols = get_env_symbols(env.parent_environment)
    else:
        parent_symbols = []
    return env.symbols + parent_symbols


def iterate_ground_actions(action, env: Environment):
    match action:
        case GroundedAction():
            yield action
        case _:
            symbols = get_env_symbols(env)
            for ga in ground_actions([action], symbols):
                yield ga


def relaxed_backward_search(
    open_fact_set: set[Fact],
    env: Environment,
    domain,
    initial_state: State,
    goal_state: State | PartialState,
):
    def achieve_fact_from_state(fact: Fact, state):
        reachable_facts = set()
        if fact in state:
            return True, set([fact])
        found_achieving_chain = False
        for A in domain.actions:
            if not can_produce(env, A, fact):
                continue
            partial_grounded_action = partially_ground_by_output(A, fact)
            for fully_grounded_action in iterate_ground_actions(
                partial_grounded_action, env
            ):
                reached_base, backward_facts = relaxed_backward_search(
                    open_fact_set,
                    env,
                    domain,
                    State(initial_state.facts | reachable_facts),
                    fully_grounded_action.precondition,
                )
                if not reached_base:
                    continue
                print("Successfully used ", fully_grounded_action)
                found_achieving_chain = True
                reachable_facts.update(backward_facts)

        if found_achieving_chain:
            print(f"returning {fact} with chain: ", [str(f) for f in reachable_facts])
        return found_achieving_chain, reachable_facts

    all_facts = set()
    if isinstance(goal_state, State):
        goal_facts = goal_state.facts
    elif isinstance(goal_state, PartialState):
        goal_facts = goal_state.positive_facts
    elif isinstance(goal_state, list):
        goal_facts = goal_state
    else:
        raise ValueError(f"Unknown goal type {type(goal_state)}")

    for g in goal_facts:
        if g not in initial_state and g not in open_fact_set:
            open_fact_set.add(g)
            success, facts = achieve_fact_from_state(g, initial_state)
            if not success:
                return False, set()
            print(f"achieved fact {g} with fact set: ", [str(f) for f in facts])
            all_facts.update(facts)
            all_facts.add(g)
        if g in initial_state:
            all_facts.add(g)

    return True, all_facts


def attempt_push_optimization(env: Environment, goal):
    pushed_goal = push(goal)
    set_symbol = Symbol("q1")
    set_def = pushed_goal.body[0]
    pushed_goal.body[0] = set_symbol

    env_opt = Environment(env, [set_symbol], {set_symbol: "splace"}) # 

    env_opt.attach_metadata(set_symbol, {"set_definition": set_def})

    # 1. Add splace fact

    # NOTE: in simplest case, we don't even need the goal regression?  Goal
    # regression should help with some combination of 1) actions preconditions
    # that we need to bind to these sets and 2) understanding when abstracting
    # the goal won't be feasible?

    # success, reachable_facts = relaxed_backward_search(
    #    set(), env2, domain, s0, State(set([pushed_goal]))
    # )


domain = parse_domain_file("move_abstraction.pddl")
print("Loaded domain: ")
print(domain)

goal = forall("p", "Place", Fact("observed", Symbol("p")))

print(push(goal))

env_symbols = [Symbol("p1"), Symbol("p2"), Symbol("p3")]
env_symbol_to_type = {}
env_symbol_to_type["p1"] = "Place"
env_symbol_to_type["p2"] = "Place"
env_symbol_to_type["p3"] = "Place"

goal2 = restrict(
    Environment(None, env_symbols, env_symbol_to_type),
    goal,
    "p",
    ["p1", "p2"],
)


for gs in generate(goal2):
    print(gs)

facts = [
    Fact("frontier", [Symbol("f1")]),
    Fact("frontier", [Symbol("f2")]),
    Fact("place", [Symbol("p1")]),
    Fact("place", [Symbol("p2")]),
    Fact("connected", [Symbol("p1"), Symbol("p2")]),
    Fact("connected", [Symbol("p2"), Symbol("p1")]),
    Fact("obj", [Symbol("o1")]),
    Fact("connected", [Symbol("f1"), Symbol("p1")]),
    Fact("connected", [Symbol("f2"), Symbol("p1")]),
    Fact("at", [Symbol("p1")]),
    Fact("visited", [Symbol("p1")]),
    Fact("splace", [Symbol("q1")]),
]
s0 = State(set(facts))

goal_state = State(set([Fact("observed", [Symbol("p2")])]))


env = Environment(None, env_symbols, env_symbol_to_type)
success, reachable_facts = relaxed_backward_search(set(), env, domain, s0, goal_state)

pushed_goal = push(goal2)
set_symbol = Symbol("q1")
set_def = pushed_goal.body[0]
pushed_goal.body[0] = set_symbol

env2 = Environment(env, [set_symbol], {set_symbol: "splace"})
env2.attach_metadata(set_symbol, {"set_definition": set_def})


success2, reachable_facts2 = relaxed_backward_search(
    set(), env2, domain, s0, State(set([pushed_goal]))
)

stream_path = "streams.pddl"
pddl_domain_path = "move_abstraction.pddl"
domain = load_full_domain(pddl_domain_path, stream_path)

planning_env, problem = get_problem_for_goal(
    domain,
    s0,
    PartialState(set([pushed_goal]), set()),
    base_env=env2,
)

plan = solve(domain.pddl_domain, problem.initial_state, problem.goal)

abc

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


domain = parse_domain_file("move_action_test.pddl")
print("Loaded move: ")
print(domain.actions)
