from omnilang import (
    Stream,
    Environment,
    State,
    Fact,
    NegatedFact,
    FullDomain,
    Problem,
)
import omnilang as oml
import subprocess
import tempfile
import os


def problem_to_clingo(
    domain: FullDomain,
    env: Environment,
    problem: Problem,
    incremental=False,
    enable_group_actions=True,
):
    """Turn a domain, environment, and problem into an encoding that Clingo can solve"""
    pddl_problem = oml.build_pddl_problem(
        domain.pddl_domain, env, problem.initial_state, problem.goal
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        problem_fn = os.path.join(tmpdirname, "problem.pddl")
        problem_fn = "problem.pddl"
        domain_fn = os.path.join(tmpdirname, "domain.pddl")
        domain_fn = "domain.pddl"

        translation_fn = os.path.join(tmpdirname, "encoding.txt")

        with open(problem_fn, "w") as fo:
            fo.write(pddl_problem.to_string())

        with open(domain_fn, "w") as fo:
            fo.write(domain.pddl_domain.to_string())

        translation_fn = "clingo_initial_translation.lp"

        command = [
            "plasp",
            "translate",
            domain_fn,
            problem_fn,
        ]
        print("command: ", " ".join(command))
        with open(translation_fn, "w") as fo:
            subprocess.run(command, stdout=fo, check=True)

        with open(translation_fn, "r") as fo:
            original_encoding = fo.readlines()

    if incremental:
        original_encoding = ["#program base."] + original_encoding

    stream_augmentation = generate_stream_clingo(
        env, domain, problem.initial_state, incremental
    )
    stream_augmentation = [s + "\n" for s in stream_augmentation]

    if enable_group_actions:
        group_action_clingo = generate_group_action_clingo(domain)
    else:
        group_action_clingo = []
    group_action_clingo = [s + "\n" for s in group_action_clingo]

    return original_encoding + stream_augmentation + group_action_clingo


def to_clingo_type_string(var, type):
    return f'has({var}, type("{type}"))'


def generated_stream_symbols_to_clingo_placeholders(env: Environment, state: State):
    """Clingo boilerplate for each symbol that a stream might generate"""
    clingo_lines = []
    for s in env.get_symbols():
        if not isinstance(s, oml.Symbol):
            continue
        if "generator" not in env.get_metadata_for_symbol(s):
            continue
        t = env.get_object_type(s)
        sid = s.identifier
        decl = f'constant(constant("{sid}")).'
        constant = f'constant("{sid}")'
        typed = f"{to_clingo_type_string(constant, t)}."
        fromstream = f'fromstream(constant("{sid}")).'
        clingo_lines += [decl, typed, fromstream]
    return clingo_lines


def to_lifted_clingo_string(fact: Fact):
    head = fact.head.replace("-", "_")
    return f"{head}({', '.join([p.identifier.upper() for p in fact.body])})"


def to_clingo_string(fact: Fact):
    head = fact.head.replace("-", "_")
    body = ", ".join([f'constant("{p.identifier}")' for p in fact.body])
    return f"{head}({body})"


def stream_to_clingo(stream: Stream):
    """Represent each stream, constraining its input and possible outputs"""
    formal_args = tuple(s.identifier.upper() for s in stream.formal_params)
    formal_outputs = tuple(s.identifier.upper() for s in stream.formal_outputs)

    formal_args_str = ", ".join((f'"{stream.name}"',) + formal_args + formal_outputs)

    # {Chosen(stream(θ))} ← θ ∈ Dom(stream; ˆW )

    output_type_restrictions = []
    for p, r in zip(stream.formal_outputs, stream.output_restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one output (type) restriction for streams. Stream {stream.name} has output {p} with restrictions {r}"
            )
        output_type_restrictions.append(
            to_clingo_type_string(p.identifier.upper(), r[0])
        )
        output_type_restrictions.append(f"fromstream({p.identifier.upper()})")
    output_type_restrictions_str = ", ".join(output_type_restrictions)

    input_type_restrictions = []
    input_realization_constraints = []
    for p, r in zip(stream.formal_params, stream.restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one input (type) restriction for streams. Stream {stream.name} has input {p} with restrictions {r}"
            )
        input_type_restrictions.append(
            to_clingo_type_string(p.identifier.upper(), r[0])
        )
        input_realization_constraints.append(f"inworld({p.identifier.upper()})")

    domain_constraints = []
    for f in stream.domain:
        if isinstance(f, Fact):
            domain_constraints.append(to_lifted_clingo_string(f))
        elif isinstance(f, NegatedFact):
            domain_constraints.append(f"not {to_lifted_clingo_string(f)}")

    stream_applicability_constraint = ", ".join(
        input_type_restrictions + input_realization_constraints + domain_constraints
    )
    max_generations = 1
    generation_constraint = f"""{{stream_generated({formal_args_str}) : {output_type_restrictions_str}}} <= {max_generations} :- {stream_applicability_constraint}."""

    stream_clingo = [generation_constraint]

    # Stream consistency
    for p in stream.formal_outputs:
        stream_clingo.append(
            f"""generated_by({p.identifier.upper()}, ({formal_args_str})) :- stream_generated({formal_args_str})."""
        )
    # generated_by(formal, (formal_args_str)) :- stream_generated(formal_args_str).

    # f ∈ Wstream ← f ∈ Certified(stream), Chosen(stream)
    for fact in stream.certificates:
        predicate = f'"{fact.head}"'
        fact_body = tuple(s.identifier.upper() for s in fact.body)

        initial_state = "true"
        lifted_fact = (predicate,) + fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        clause = f"""initialState({var}, value({var}, {initial_state})) :- stream_generated({formal_args_str})."""
        stream_clingo.append(clause)

        fact_str = to_lifted_clingo_string(fact)
        static_clause = f"""{fact_str} :- stream_generated({formal_args_str})."""
        stream_clingo.append(static_clause)

    return stream_clingo


def make_general_stream_constraints():
    """Ensure that each symbol is only generated by one stream, and that we can track which possible symbols are "really" in the world"""
    # Stream consistency
    stream_consistency = ":- generated_by(X, Y), generated_by(X, Z), Y != Z."

    inworld_tracking = "inworld(X) :- generated_by(X, _)."
    inworld_default = 'inworld(X) :- not fromstream(X), has(X, type("object")).'

    clingo_lines = [stream_consistency, inworld_tracking, inworld_default]
    return clingo_lines


def clingofy_initial_state(state: State):
    """Turn the initial problem state into clingo facts so that we can do static reasoning without pollution initialState"""
    lines = [f"{to_clingo_string(f)}." for f in state.facts]
    return lines


def derive_initial_states(derived_facts: list[oml.DerivedStreamFacts]):
    """Support "derived streams" that add additional static facts"""

    # head(B1, ..., BN) :- type restrictions, domain.
    # initialState(variable(head(B1, ..., BN)), value(variable((head(B1,...,BN))), true)) :- type restrictions, domain.

    output_clingo = []

    for df in derived_facts:
        input_type_restrictions = []
        input_realization_constraints = []
        for p, r in zip(df.formal_params, df.restrictions):
            if len(r) != 1:
                raise Exception(
                    f"Currently only support one input (type) restriction for streams. Stream {df.name} has input {p} with restrictions {r}"
                )
            input_type_restrictions.append(
                to_clingo_type_string(p.identifier.upper(), r[0])
            )
            input_realization_constraints.append(f"inworld({p.identifier.upper()})")

        domain_constraints = []
        for f in df.domain:
            if isinstance(f, Fact):
                domain_constraints.append(to_lifted_clingo_string(f))
            elif isinstance(f, NegatedFact):
                domain_constraints.append(f"not {to_lifted_clingo_string(f)}")

        stream_applicability_constraint = ", ".join(
            input_type_restrictions + input_realization_constraints + domain_constraints
        )

        formal_args = tuple(s.identifier.upper() for s in df.formal_params)
        formal_args_str = ", ".join((f'"{df.name}"',) + formal_args)
        stream_derived = f"""stream_derived({formal_args_str}) :- {stream_applicability_constraint}."""
        output_clingo.append(stream_derived)
        for cert in df.certificates:
            predicate = f'"{cert.head}"'
            fact_body = tuple(s.identifier.upper() for s in cert.body)
            initial_state = "true"
            lifted_fact = (predicate,) + fact_body
            lifted_fact_str = ", ".join(lifted_fact)
            var = f"""variable(({lifted_fact_str}))"""

            initialState = f"""initialState({var}, value({var}, {initial_state})) :- stream_derived({formal_args_str})."""
            output_clingo.append(initialState)

            fact = to_lifted_clingo_string(cert)
            static_fact = f"{fact} :- stream_derived({formal_args_str})."
            output_clingo.append(static_fact)

    return output_clingo


def is_group_param(s: oml.Symbol):
    return s.identifier.startswith("&")


def group_action_to_clingo(action: oml.LiftedAction):
    action_list = [f'"{action.name}"'] + [
        p.identifier[1:].upper() for p in action.params
    ]
    action_string = ", ".join(action_list)
    action_header = f"action(({action_string}))"

    input_type_restrictions = []
    input_realization_constraints = []
    input_group_constraints = []
    for p, r in zip(action.params, action.param_restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one input (type) restriction for actions. Stream {action.name} has input {p} with restrictions {r}"
            )
        input_type_restrictions.append(
            to_clingo_type_string(p.identifier.upper()[1:], r[0])
        )
        input_realization_constraints.append(f"inworld({p.identifier.upper()[1:]})")
        if is_group_param(p):
            input_group_constraints.append(f"group({p.identifier.upper()[1:]})")

    action_applicability_constraint = ", ".join(
        input_type_restrictions
        + input_realization_constraints
        + input_group_constraints
    )
    clingo_lines = [f"action({action_header}) :- {action_applicability_constraint}."]

    for constraint in action.precondition:
        predicate = f'"{constraint.head}"'
        fact_body = tuple(s.identifier.upper() for s in constraint.body)
        group_syms = [s for s in constraint.body if is_group_param(s)]
        if isinstance(constraint, oml.Fact):
            condition = "true"
        else:
            assert isinstance(constraint, oml.NegatedFact)
            condition = "false"

        lifted_fact_body = []
        idx = 0
        for f in fact_body:
            if f.startswith("&"):
                lifted_fact_body.append(f"Y{idx}")
                idx += 1
            else:
                if f.startswith("?"):
                    f = f[1:]
                lifted_fact_body.append(f)

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        for idx, gs in enumerate(group_syms):
            requirements.append(f"ingroup({gs.identifier.upper()[1:]}, Y{idx})")
        requirements_str = ", ".join(requirements)
        clingo_lines.append(
            f"precondition({action_header}, {var}, value({var}, {condition})) :- {requirements_str}."
        )

    for constraint in action.positive_effect:
        predicate = f'"{constraint.head}"'
        fact_body = tuple(s.identifier.upper() for s in constraint.body)
        group_syms = [s for s in constraint.body if is_group_param(s)]

        lifted_fact_body = []
        idx = 0
        for f in fact_body:
            if f.startswith("&"):
                lifted_fact_body.append(f"Y{idx}")
                idx += 1
            else:
                if f.startswith("?"):
                    f = f[1:]
                lifted_fact_body.append(f)

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        for idx, gs in enumerate(group_syms):
            requirements.append(f"ingroup({gs.identifier.upper()[1:]}, Y{idx})")
        requirements_str = ", ".join(requirements)

        clingo_lines.append(
            f"postcondition({action_header}, {var}, value({var}, true)) :- {requirements_str}."
        )
    for constraint in action.negative_effect:
        predicate = f'"{constraint.head}"'
        fact_body = tuple(s.identifier.upper() for s in constraint.body)
        group_syms = [s for s in constraint.body if is_group_param(s)]

        lifted_fact_body = []
        idx = 0
        for f in fact_body:
            print("F: ", f)
            if f.startswith("&"):
                lifted_fact_body.append(f"Y{idx}")
                idx += 1
            else:
                print("not &")
                if f.startswith("?"):
                    print("starts ?")
                    f = f[1:]
                print(f)
                lifted_fact_body.append(f)

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        for idx, gs in enumerate(group_syms):
            requirements.append(f"ingroup({gs.identifier.upper()[1:]}, Y{idx})")
        requirements_str = ", ".join(requirements)
        clingo_lines.append(
            f"postcondition({action_header}, {var}, value({var}, false)) :- {requirements_str}."
        )

    return clingo_lines


def generate_group_action_clingo(domain: FullDomain):
    clingo_lines = [
        """
{ingroup(X, Y)} :- group(X), has(X, type(T)), has(Y, type(T)), not group(Y).
inworld(Y) :- group(X), ingroup(X, Y), inworld(X).
    """
    ]
    for action in domain.pddl_domain.group_actions:
        clingo_lines += group_action_to_clingo(action)

    return clingo_lines


def generate_stream_clingo(
    env0: Environment, domain: FullDomain, s0: State, incremental: bool
):
    """Generate the clingo associated with all streams and derived streams"""
    streams = domain.streams

    # pddl_domain = domain.pddl_domain
    # generated_env, generated_state = expand_streams(
    #     env0, pddl_domain, streams, s0
    # )  # Generate predicted places
    # generated_env, generated_state = expand_streams(
    #     generated_env, pddl_domain, streams, generated_state
    # )  # Generate predicted objects
    # TODO: generalize the number of streams we need to evaluate. See
    # generate_bindable_world and generate_unsatisfying_consistent_world

    stream_symbol_defs = generated_stream_symbols_to_clingo_placeholders(env0, s0)

    stream_derived_initial_states = derive_initial_states(domain.derived_stream_facts)

    output_clingo = ["%%%%%%% Streams %%%%%%%%%\n"]
    # if incremental:
    #    output_clingo.append("#program streams.")

    for d in stream_symbol_defs:
        output_clingo.append(d)

    for s in streams:
        c = stream_to_clingo(s)
        output_clingo += c

    lines = make_general_stream_constraints()
    output_clingo += lines

    output_clingo += clingofy_initial_state(s0)

    output_clingo += stream_derived_initial_states

    # Necessary to enforce that the span of the belief state is contained within the goal.

    # output_clingo += ["#show goal/2."]
    output_clingo += [
        'pholds(Val) :- holds(derivedVariable("derived-predicate-1"), Val, 0).'
    ]
    # output_clingo += ["#show pholds/1."]

    output_clingo += ["zholds(Val) :- holds(Var, Val, 0)."]
    # output_clingo += ["#show zholds/1."]

    if incremental:
        output_clingo += ["#program bsp_restriction."]
    output_clingo += [":- goal(Variable, Value), holds(Variable, Value, 0)."]

    n_string_args = set(len(s.formal_params) + len(s.formal_outputs) for s in streams)
    for n in n_string_args:
        output_clingo += ["#show inworld/1."]

    # output_clingo += ["#show inworld/1."]
    # output_clingo += ["#show fromstream/1."]
    # output_clingo += ["#show holds/3."]
    # output_clingo += ["#show precondition/4."]

    return output_clingo


def pddl_problem_to_state(problem: oml.PddlProblemInstance):
    s0 = State(set(problem.initial_facts))
    symbols = problem.objects
    symbol_to_type = problem.objects_to_type
    return s0, Environment(None, symbols, symbol_to_type)
