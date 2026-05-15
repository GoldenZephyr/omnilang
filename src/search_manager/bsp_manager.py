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


def add_groups(env0, s0, groups: dict[str, str]):
    symbols = [oml.Symbol(k) for k in groups]
    dummy_types = {k: "group" for k in groups}

    env = oml.Environment(env0, symbols, dummy_types)
    for groupname, grouptype in groups.items():
        env.attach_metadata(oml.Symbol(groupname), {"group_type": grouptype})
    group_facts = set(oml.Fact("group", [oml.Symbol(s)]) for s in groups)
    s0_aug = oml.State(s0.facts | group_facts)
    return env, s0_aug


class BspManager:
    def __init__(
        self,
        domain: oml.FullDomain,
        env: oml.Environment,
        problem: oml.Problem,
        enable_groups=True,
        n_models=10,
    ):
        self.domain = domain
        self.env = env
        self.problem = problem
        self.enable_groups = enable_groups

        self.solutions = {}

        # Number of models to generate per (belief-level, horizon) pair
        self.n_models = n_models

    def get_extra_symbols_at_belief_level(self, belief_level):
        base_generateable_types = get_output_types(self.domain.streams)
        generateable_types = set(base_generateable_types)
        # For self-referential streams, a stream might only be able to generate a *subtype* of its listed output type
        for t in base_generateable_types:
            generateable_types |= set(self.env.get_subtypes_of_type(t))

        extra_symbols = {}

        for t in generateable_types:
            for idx in range(belief_level):
                extra_symbols[oml.Symbol(f"s{t}{idx}")] = t
        return extra_symbols

    def get_group_symbols_at_belief_level(self, belief_level):
        groups_per_type = 1
        groups_to_make = {}
        for t in self.domain.pddl_domain.get_group_types():
            for idx in range(groups_per_type):
                groups_to_make[f"group_{t}{idx}"] = t
        return groups_to_make

    def world_fully_generated(self, solution, belief_level):
        new_env, new_facts, plan = solution
        extra_symbols = self.get_extra_symbols_at_belief_level(belief_level)
        generated_symbols = new_env.get_symbols()
        for s in extra_symbols.keys():
            if s not in generated_symbols:
                return False
        return True

    def search(
        self,
        belief_level_bounds,
        plan_length_bounds,
        generator=False,
        take_first_plan=False,
    ):
        min_plan_length, max_plan_length = plan_length_bounds
        min_belief_level, max_belief_level = belief_level_bounds
        # search strategy is: Start at belief level B. Increase plan length to max level, or level where world is fully-generated. Then, increase belief level, but keep search level

        current_min_horizon = plan_length_bounds[0]

        have_found_a_plan = False

        managers = {}
        generators = {}

        for belief_level in range(min_belief_level, max_belief_level):
            if have_found_a_plan and take_first_plan:
                break
            for horizon in range(current_min_horizon, max_plan_length):
                manager, generator, solution = self.search_at_level(
                    belief_level, horizon
                )
                if solution is None:
                    continue
                have_found_a_plan = True
                self.solutions[(belief_level, horizon)] = solution
                managers[(belief_level, horizon)] = manager
                generators[(belief_level, horizon)] = generator
                # break # necessary if we want to take very first example
                if self.world_fully_generated(solution, belief_level):
                    break
            if have_found_a_plan:
                current_min_horizon = horizon

        return managers, generators, self.solutions

    def search_at_level(self, level: int, horizon: int):
        extra_symbols = self.get_extra_symbols_at_belief_level(level)
        print(
            f"Searching at (level {level}, horizon {horizon}), with extra symbols {extra_symbols}."
        )
        if self.enable_groups:
            groups_to_add = self.get_group_symbols_at_belief_level(level)
            env, s0 = add_groups(self.env, self.problem.initial_state, groups_to_add)
            problem = oml.Problem(s0, self.problem.goal)
        else:
            env = self.env
            problem = self.proble

        generated_env = oml.Environment(env, extra_symbols.keys(), extra_symbols)
        for s in extra_symbols:
            generated_env.attach_metadata(s, {"generator": True})

        manager = solve_clingo_problem(
            self.domain,
            generated_env,
            problem,
            min_horizon=horizon,
            max_horizon=horizon + 1,
            n_models=self.n_models,
        )

        if manager is None:
            print(f"No plan found with belief level {level}, horizon {horizon}.")
            return None, None, None

        new_env, new_facts, plan = manager.get_next_plan_and_world(
            self.env, generated_env, self.domain
        )

        # generator = lambda: manager.get_next_plan_and_world(
        #    self.env, generated_env, self.domain
        # )

        def generator(manager=manager):
            ne, nf, p = manager.get_next_plan_and_world(
                self.env, generated_env, self.domain
            )
            print(f"Calling generator, n plans: {len(manager.plans)}")
            manager.plans = manager.plans[:-1]
            return ne, nf, p

        return manager, generator, (new_env, new_facts, plan)
