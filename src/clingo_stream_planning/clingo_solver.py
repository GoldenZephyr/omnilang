import clingo
from clingo_stream_planning.clingo_builder import problem_to_clingo
import clingo_stream_planning.encodings
import omnilang as oml
from importlib.resources import as_file, files


def process_clingo_arg(arg: clingo.Function):
    assert arg.name == "constant"
    return arg.arguments[0].string


def process_clingo_action(action):
    action_name = action[0].string
    args = tuple(process_clingo_arg(arg) for arg in action[1:])
    return (action_name,) + args


def get_state_from_clingo(facts):
    initial_state = []
    for f in facts:
        match f.type:
            case f.type.Function:
                name = f.name
                if name != "trueInitialState":
                    continue
                var = f.arguments[0]
                arg0 = var.arguments[0]
                if arg0.type == f.type.String:
                    initial_state.append(oml.Fact(arg0.string, []))
                    continue
                predicate = arg0.arguments[0].string
                args = arg0.arguments[1:]
                initial_state.append(
                    oml.Fact(
                        predicate, [oml.Symbol(process_clingo_arg(s)) for s in args]
                    )
                )
            case _:
                pass

    return set(initial_state)


def clingo_solution_to_plan(facts):
    actions = []
    for f in facts:
        match f.type:
            case f.type.Function:
                name = f.name
                if name != "occurs":
                    continue
                action, order = f.arguments
                actions.append(
                    (order.number, process_clingo_action(action.arguments[0].arguments))
                )
            case _:
                pass

    plan = [t[1] for t in sorted(actions)]

    return plan


def clingo_solution_to_groupings(facts):
    groupings = {}
    for f in facts:
        match f.type:
            case f.type.Function:
                name = f.name
                if name != "ingroup":
                    continue
                group, member = f.arguments
                group = group.arguments[0].string
                member = member.arguments[0].string
                if group not in groupings:
                    groupings[group] = [member]
                else:
                    groupings[group].append(member)
            case _:
                pass

    return groupings


def get_grounded_io(stream: oml.Stream, clingo_args):
    grounded_args = [
        oml.Symbol(a.arguments[0].string)
        for a in clingo_args[: len(stream.formal_params)]
    ]
    grounded_outputs = [
        oml.Symbol(a.arguments[0].string)
        for a in clingo_args[len(stream.formal_params) :]
    ]
    return grounded_args, grounded_outputs


def extend_env_with_clingo_world(
    base_env: oml.Environment,
    og_generated_env: oml.Environment,
    domain: oml.FullDomain,
    clingo_facts,
):
    streams_to_apply = set()
    new_facts = []
    for f in clingo_facts:
        match f.type:
            case f.type.Function:
                name = f.name
                if name != "stream_generated":
                    continue

                args = f.arguments[0]
                stream_name = args.arguments[0].string
                stream = domain.lookup_stream(stream_name)

                grounded_args, grounded_outputs = get_grounded_io(
                    stream, args.arguments[1:]
                )

                # We can't compute the metadata here because we aren't
                # guaranteed to be iterating in topological order
                gs, _ = stream.apply(
                    grounded_args,
                    environment=None,
                    grounded_outputs=grounded_outputs,
                    generate_metadata=False,
                )
                new_facts += gs.output_facts

                streams_to_apply.add(gs)

    updated_env = base_env
    while len(streams_to_apply) > 0:
        new_streams_to_apply = set()
        applied_something = False
        new_symbols = []
        new_symbols_to_type = {}
        new_symbol_metadata = []
        for s in streams_to_apply:
            can_apply = all(updated_env.contains(a) for a in s.inputs)
            if can_apply:
                applied_something = True
                for sym in s.output_symbols:
                    new_symbols.append(sym)
                    new_symbols_to_type[sym] = og_generated_env.get_object_type(sym)
                symbol_metadata = domain.lookup_stream(s.name).generate_metadata(
                    updated_env, s.inputs, s.output_symbols
                )
                for m in symbol_metadata.values():
                    m["generator"] = s
                new_symbol_metadata.append(symbol_metadata)

            else:
                new_streams_to_apply.add(s)
        streams_to_apply = new_streams_to_apply
        if not applied_something:
            stream_text = ", ".join([f"{s.name}({s.inputs})"])
            raise Exception(
                f"Cannot apply all streams. Streams that cannot be applied: {stream_text}"
            )
        updated_env = oml.Environment(updated_env, new_symbols, new_symbols_to_type)

        for nsm in new_symbol_metadata:
            for s, m in nsm.items():
                updated_env.attach_metadata(s.identifier, m)

    return updated_env, new_facts


def solve_clingo_problem(
    domain: oml.FullDomain, env: oml.Environment, problem: oml.Problem, max_horizon=20
):
    full_clingo = problem_to_clingo(domain, env, problem)

    clingo_problem_path = "full_problem.lp"
    with open(clingo_problem_path, "w") as fo:
        fo.writelines(full_clingo)

    manager = PlanManager()
    for horizon in range(1, max_horizon):
        print("Trying horizon: ", horizon)
        ctl = clingo.Control(["-c", f"horizon={horizon}"])
        ctl.configuration.solve.models = 13

        with as_file(
            files(clingo_stream_planning.encodings).joinpath("sequential-horizon.lp")
        ) as path:
            ctl.load(str(path))

        # ctl.load("plasp/encodings/sequential-horizon.lp")
        ctl.load(clingo_problem_path)

        ctl.ground([("base", [])])

        result = ctl.solve(on_model=manager.on_model)

        if result.satisfiable:
            return manager

    return None


def solve_clingo_problem_incremental(
    domain: oml.FullDomain, env: oml.Environment, problem: oml.Problem, max_horizon=20
):
    full_clingo = problem_to_clingo(domain, env, problem, incremental=True)

    clingo_problem_path = "full_problem.lp"
    with open(clingo_problem_path, "w") as fo:
        fo.writelines(full_clingo)

    ctl = clingo.Control()
    with as_file(
        files(clingo_stream_planning.encodings).joinpath("sequential-incremental.lp")
    ) as path:
        ctl.load(str(path))
    ctl.load(clingo_problem_path)

    # ctl.ground([("instance", [])])
    ctl.ground([("base", [])])
    ctl.ground([("bsp_restriction", [])])
    ctl.configuration.solve.models = 0

    manager = PlanManager()
    for t in range(1, max_horizon + 1):
        print("Trying incremental step: ", t)

        ctl.ground([("step", [clingo.Number(t)])])
        ctl.ground([("check", [clingo.Number(t)])])

        result = ctl.solve(on_model=manager.on_model)

        if result.satisfiable:
            return manager

    return None


class PlanManager:
    def __init__(self):
        self.plans = []

    def on_model(self, model):
        atoms = model.symbols(shown=True)
        self.plans.append(atoms)

    def get_next_solution(self):
        return self.plans[-1]

    def get_next_plan(self):
        plan = clingo_solution_to_plan(self.get_next_solution())
        return plan

    def get_next_plan_and_world(
        self, base_env, og_generated_env, domain: oml.FullDomain
    ):
        next_sol = self.get_next_solution()
        env, new_facts = extend_env_with_clingo_world(
            base_env, og_generated_env, domain, next_sol
        )
        w0_from_clingo = get_state_from_clingo(next_sol)
        plan = clingo_solution_to_plan(next_sol)

        return (
            env,
            oml.State(w0_from_clingo),
            plan,
        )

    def get_groupings(self) -> dict[str, str]:
        return clingo_solution_to_groupings(self.get_next_solution())
