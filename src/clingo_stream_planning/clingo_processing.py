from clingo_stream_planning.clingo_solver import PlanManager
import omnilang as oml


def extract_clingo_solution(
    env: oml.Environment,
    og_generated_env: oml.Environment,
    domain: oml.FullDomain,
    problem: oml.Problem,
    solution_manager: PlanManager,
):
    updated_env, state_from_clingo, plan = solution_manager.get_next_plan_and_world(
        env, og_generated_env, domain
    )

    # the original problem may have some facts that were not represented in the
    # original state, and clingo might have some facts not in original state.

    fused_state = oml.State(problem.initial_state.facts | state_from_clingo.facts)
    return updated_env, fused_state, plan
