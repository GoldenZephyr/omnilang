from clingo_stream_planning.clingo_solver import PlanManager
import omnilang as oml


def extract_clingo_solution(
    env: oml.Environment,
    og_generated_env: oml.Environment,
    domain: oml.FullDomain,
    problem: oml.Problem,
    solution_manager: PlanManager,
):
    updated_env, updated_s0, plan = solution_manager.get_next_plan_and_world(
        env, og_generated_env, domain
    )
    updated_problem = oml.Problem(updated_s0, problem.goal)
    return updated_env, updated_problem, plan
