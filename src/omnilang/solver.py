# ruff: noqa: F811
from omnilang.mdp_states import generate, QuantifiedSet, PartialState, negate
from dsg_pddl.pddl_planning import solve_pddl
from dsg_pddl.pddl_grounding import PddlProblem, GroundedPddlProblem, PddlDomain
from omnilang.streams import group_objects_by_type
from plum import dispatch


# @dispatch
# def to_pddl_facts(goal: QuantifiedSet):
#    return tuple(a.to_tuple() for a in generate(goal))


@dispatch
def to_pddl_goal(goal: QuantifiedSet):
    facts = tuple(a.to_tuple() for a in generate(goal))
    print("facts:", facts)
    print("\n\n")
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


# @dispatch
# def to_pddl_facts(goal: PartialState):
#    return tuple(f.to_tuple() for f in goal.positive_facts) + tuple(
#        negate(f).to_tuple() for f in goal.negative_facts
#    )


def solve(domain: PddlDomain, initial_state, goal: PartialState):
    # tuple_goal = ("and",) + to_pddl_facts(goal)
    tuple_goal = to_pddl_goal(goal)
    objects = group_objects_by_type(domain, initial_state.facts)
    print("objects by type: ")
    print(objects)
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
