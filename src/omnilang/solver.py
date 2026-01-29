# ruff: noqa: F811
from omnilang.mdp_states import (
    QuantifiedSet,
    PartialState,
    negate,
    Symbol,
    Fact,
    State,
)
from omnilang.mdp_state_operations import push, generate
from omnilang.environment import Environment
from dsg_pddl.pddl_planning import solve_pddl
from dsg_pddl.pddl_grounding import PddlProblem, GroundedPddlProblem, PddlDomain
from omnilang.streams import group_objects_by_type
from plum import dispatch
from omnilang.construct_problem import expand_streams, Problem


@dispatch
def to_pddl_goal(goal: QuantifiedSet):
    facts = tuple(a.to_tuple() for a in generate(goal))
    match goal.quantifier:
        case "exists":
            junction = "or"
        case "forall":
            junction = "and"
        case _:
            raise ValueError(f"Unknown goal quantifier {goal.quantifier}")
    return (junction,) + facts


@dispatch
def to_pddl_goal(goal: PartialState):
    positives = tuple(f.to_tuple() for f in goal.positive_facts)
    negatives = tuple(negate(f).to_tuple() for f in goal.negative_facts)
    return ("and",) + positives + negatives


def solve_existential(
    env: Environment,
    domain: PddlDomain,
    initial_state,
    goal: QuantifiedSet,
):
    max_depth = 5
    for extra_depth in range(max_depth):
        plan = solve(domain, initial_state, goal)
        if plan is not None:
            break
        env, initial_state = expand_streams(env, domain.streams, initial_state)
        print("Solving failed with existential quantifier. Trying higher stream depth!")
        for f in initial_state.facts:
            print(f)
    return env, plan


def attempt_push_optimization(env: Environment, problem: Problem):
    assert isinstance(problem.goal, QuantifiedSet)

    pushed_goal = push(problem.goal)
    set_symbol = Symbol("q1")
    set_def = pushed_goal.body[0]
    pushed_goal.body[0] = set_symbol

    # TODO: How do we get the type to associate with the set?
    symbol_type = "splace"
    env_opt = Environment(env, [set_symbol], {set_symbol: symbol_type})
    env_opt.attach_metadata(set_symbol, {"set_definition": set_def})

    extra_facts = set([Fact(symbol_type, [set_symbol])])

    updated_state = State(extra_facts | problem.initial_state.facts)
    # TODO: There might be more facts related to the domain of the quantifier that we want t  o add as well?

    # NOTE: in simplest case, we don't even need the goal regression?  Goal
    # regression should help with some combination of 1) actions preconditions
    # that we need to bind to these sets and 2) understanding when abstracting
    # the goal won't be feasible?

    # success, reachable_facts = relaxed_backward_search(
    #    set(), env2, domain, s0, State(set([pushed_goal]))
    # )

    return env_opt, Problem(updated_state, PartialState(set([pushed_goal]), set()))


def modal_solve(
    env: Environment,
    domain: PddlDomain,
    initial_state,
    goal: PartialState | QuantifiedSet,
):
    if isinstance(goal, QuantifiedSet):
        print("\n\nTrying push-solve optimization!!!")
        final_env, updated_problem = attempt_push_optimization(
            env, Problem(initial_state, goal)
        )
        try:
            plan = solve(domain, updated_problem.initial_state, updated_problem.goal)
        except Exception:
            plan = None

        if plan is not None:
            return final_env, plan
        print("Push-solve optimization failed!\n\n")

    if isinstance(goal, QuantifiedSet) and goal.quantifier == "exists":
        return solve_existential(env, domain, initial_state, goal)

    return env, solve(domain, initial_state, goal)


def solve(domain: PddlDomain, initial_state, goal: PartialState | QuantifiedSet):
    tuple_goal = to_pddl_goal(goal)
    objects = group_objects_by_type(domain, initial_state.facts)
    problem = PddlProblem(
        name="test_explore",
        domain=domain.name,
        # TODO: "T" is temporary until we properly deal with types vs unary predicates
        objects={k + "T": [o.identifier for o in objs] for k, objs in objects.items()},
        initial_facts=[i.to_tuple() for i in initial_state.facts],
        goal=tuple_goal,
        optimizing=False,
    )

    problem_string = problem.to_string()

    grounded_problem = GroundedPddlProblem(domain, problem_string, {})
    plan = solve_pddl(grounded_problem)
    return plan
