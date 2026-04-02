import omnilang as oml
from clingo_stream_planning import (
    solve_clingo_problem,
)


def get_output_types(streams: list[oml.Stream]):
    types = set()
    for s in streams:
        for output_restriction in s.output_restrictions:
            types.add(output_restriction[0])
    return types


class BspManager:
    def __init__(
        self, domain: oml.FullDomain, env: oml.Environment, problem: oml.Problem
    ):
        self.domain = domain
        self.env = env
        self.problem = problem

        self.solutions = {}

        # Number of models to generate per (belief-level, horizon) pair
        self.n_models = 10

    def get_extra_symbols_at_belief_level(self, belief_level):
        generateable_types = get_output_types(self.domain.streams)

        extra_symbols = {}

        for t in generateable_types:
            for idx in range(belief_level):
                extra_symbols[oml.Symbol(f"s{t}{idx}")] = t
        return extra_symbols

    def world_fully_generated(self, solution, belief_level):
        new_env, new_facts, plan = solution
        extra_symbols = self.get_extra_symbols_at_belief_level(belief_level)
        generated_symbols = new_env.get_symbols()
        for s in extra_symbols.keys():
            if s not in generated_symbols:
                return False
        return True

    def search(self, belief_level_bounds, plan_length_bounds, generator=False):
        min_plan_length, max_plan_length = plan_length_bounds
        min_belief_level, max_belief_level = belief_level_bounds
        # search strategy is: Start at belief level B. Increase plan length to max level, or level where world is fully-generated. Then, increase belief level, but keep search level

        current_min_horizon = 1

        have_found_a_plan = False

        for belief_level in range(min_belief_level, max_belief_level):
            for horizon in range(current_min_horizon, max_plan_length):
                solution = self.search_at_level(belief_level, horizon)
                if solution is None:
                    continue
                have_found_a_plan = True
                self.solutions[(belief_level, horizon)] = solution
                if self.world_fully_generated(solution, belief_level):
                    # if belief_level > 1:
                    #    abc
                    break
                # if generator:
                #    yield solution
            if have_found_a_plan:
                current_min_horizon = horizon

        return self.solutions

    def search_at_level(self, level: int, horizon: int):
        extra_symbols = self.get_extra_symbols_at_belief_level(level)
        print(
            f"Searching at (level {level}, horizon {horizon}), with extra symbols {extra_symbols}."
        )
        generated_env = oml.Environment(self.env, extra_symbols.keys(), extra_symbols)
        for s in extra_symbols:
            generated_env.attach_metadata(s, {"generator": True})

        manager = solve_clingo_problem(
            self.domain,
            generated_env,
            self.problem,
            min_horizon=horizon,
            max_horizon=horizon + 1,
            n_models=self.n_models,
        )

        if manager is None:
            print(f"No plan found with belief level {level}, horizon {horizon}.")
            return None

        new_env, new_facts, plan = manager.get_next_plan_and_world(
            self.env, generated_env, self.domain
        )
        return new_env, new_facts, plan
