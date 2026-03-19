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


def clingo_solution_to_plan(facts):
    actions = []
    for f in facts:
        match f.type:
            case f.type.Function:
                name = f.name
                if name != "occurs":
                    print("skipping ", name)
                    continue
                action, order = f.arguments
                actions.append(
                    (order.number, process_clingo_action(action.arguments[0].arguments))
                )
            case _:
                print("skipping (not a function)", f)
                print(type(f))
                pass

    print("actions: ", actions)
    plan = [t[1] for t in sorted(actions)]

    return plan


def get_grounded_io(stream: oml.Stream, clingo_args):
    grounded_args = [
        oml.Symbol(a[0].string) for a in clingo_args[: len(stream.formal_params)]
    ]
    grounded_outputs = [
        oml.Symbol(a[0].string) for a in clingo_args[len(stream.formal_params) :]
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

                print("stream-generated fact: ", f)
                stream_name = f.arguments[0].string
                stream = domain.lookup_stream(stream_name)

                grounded_args, grounded_outputs = get_grounded_io(
                    stream, f.arguments[1:]
                )

                # We can't compute the metadata here because we aren't
                # guaranteed to be iterating in topological order
                gs, _ = stream.apply(
                    grounded_args,
                    environment=None,
                    grounded_outputs=grounded_outputs,
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
                for sym in s.inputs:
                    new_symbols.append(sym)
                    new_symbols_to_type[sym] = og_generated_env.get_object_type(sym)
                symbol_metadata = domain.lookup_stream(s.name).generate_metadata(
                    updated_env, s.inputs, s.output_facts
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
    for horizon in range(max_horizon):
        print("Trying horizon: ", horizon)
        ctl = clingo.Control(["-c", f"horizon={horizon}"])
        ctl.configuration.solve.models = 1

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


class PlanManager:
    def __init__(self):
        self.plans = []

    def on_model(self, model):
        atoms = model.symbols(shown=True)
        print("Model:")
        for a in atoms:
            print(a)

        self.plans.append(atoms)

    def get_next_plan(self):
        plan = clingo_solution_to_plan(self.plans[0])
        return plan

    def get_next_plan_and_world(
        self, base_env, og_generated_env, domain: oml.FullDomain
    ):
        env, new_facts = extend_env_with_clingo_world(
            base_env, og_generated_env, domain, self.plans[0]
        )
        plan = clingo_solution_to_plan(self.plans[0])

        return (
            env,
            new_facts,
            plan,
        )
