from clingo_stream_planning import PlanManager
import omnilang as oml


def extract_clingo_solution(
    env: oml.Environment, problem: oml.Problem, solution_manager: PlanManager
):
    updated_env, updated_s0, plan = solution_manager.get_next_plan_and_world()
    updated_problem = oml.Problem(updated_s0, problem.goal)
    return updated_env, updated_problem, plan
