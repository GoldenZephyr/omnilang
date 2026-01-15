from testing import generate
from dsg_pddl.pddl_planning import solve_pddl
from dsg_pddl.pddl_grounding import PddlProblem, GroundedPddlProblem, PddlDomain
from streams import group_objects_by_type


def solve(domain: PddlDomain, initial_state, goal):
    tuple_goal = ("and",) + tuple(a.to_tuple() for a in generate(goal))
    objects = group_objects_by_type(domain, initial_state.facts)
    problem = PddlProblem(
        name="test_explore",
        domain=domain.domain_name,
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
