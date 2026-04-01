from omnilang import (
    Stream,
    Environment,
    State,
    Fact,
    NegatedFact,
    FullDomain,
    Problem,
    Conjunction,
    Disjunction,
    UniversalQuantifier,
    ExistentialQuantifier,
    Negation,
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
    enable_derived_predicates=True,
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

    original_encoding = filter_original_encoding(env, domain, original_encoding)

    if incremental:
        original_encoding = ["#program base."] + original_encoding

    stream_augmentation = generate_stream_clingo(
        env, domain, problem.initial_state, incremental
    )
    stream_augmentation = [s + "\n" for s in stream_augmentation]

    if enable_group_actions:
        group_action_clingo = generate_group_action_clingo(domain)
        group_action_clingo += generate_group_types(domain, env, problem)
        group_action_clingo += generate_groupable_predicates(domain, env, problem)
    else:
        group_action_clingo = []
    group_action_clingo = [s + "\n" for s in group_action_clingo]

    if enable_derived_predicates:
        derived_predicate_clingo = generate_derived_predicate_clingo(domain)
        derived_predicate_clingo = [s + "\n" for s in derived_predicate_clingo]
    else:
        derived_predicate_clingo = []

    optimization_clingo = generate_optimization_clingo(domain, env, problem)
    optimization_clingo = [s + "\n" for s in optimization_clingo]

    show_init_state_clingo = generate_show_init_state_clingo()
    show_init_state_clingo = [s + "\n" for s in show_init_state_clingo]

    return (
        original_encoding
        + stream_augmentation
        + group_action_clingo
        + derived_predicate_clingo
        + optimization_clingo
        + show_init_state_clingo
    )


def filter_original_encoding(
    env: Environment, domain: FullDomain, original_encoding: list[str]
):
    """This is a rather dumb hack to account for the fact that editing the
    plasp clingo translator would be a pain"""

    derived_predicates = [d.name for d in domain.pddl_domain.derived_predicates]

    def line_ok(line):
        return all(
            not line.startswith(f'variable(variable(("{dp}"')
            for dp in derived_predicates
        )

    return [line for line in original_encoding if line_ok(line)]


def generate_derived_predicate_clingo(domain: FullDomain):
    derived_predicates = domain.pddl_domain.derived_predicates
    if derived_predicates is None:
        return []

    lines = []
    for dp in derived_predicates:
        aux_dp, original_dp = derived_predicate_to_clingo(dp)

        print("aux dp clingo: ")
        for l in aux_dp:
            print(l)
        print("og dp clingo: ")
        for l in original_dp:
            print(l)
        lines += aux_dp + original_dp

    return lines


def derived_predicate_to_clingo(dp: oml.DerivedPredicate, counter=[0], prefix=None):
    # (forall (?p - place) (implies (possibly-object ?o ?p) (observed ?p)))
    # derivedPredicate({derived_predicate}) :-

    match dp.body:
        case oml.Disjunction():
            trigger_type = "or"
        case _:
            trigger_type = "and"

    parms = ", ".join(map(variable_to_clingo, dp.params))

    constraints = []
    for p, t in zip(dp.params, dp.types):
        var = variable_to_clingo(p)
        constraints.append(to_clingo_type_string(var, t))
        constraints.append(f"inworld({var})")
    input_constraints = ", ".join(constraints)

    if len(parms) > 0:
        parm_str = ", " + parms
    else:
        parm_str = ""
    derived_var = f'variable(("{dp.name}" {parm_str}))'
    variable_args = f'("{dp.name}", {parms})'
    derived_predicate = f"derivedPredicate({variable_args})"

    if len(parms) > 0:
        lines = [f"derivedVariable(variable({variable_args})) :- {input_constraints}."]
    else:
        lines = [f"derivedVariable(variable({variable_args}))."]
    head = f"derivedPredicate({derived_predicate}, type({trigger_type}))"
    lines.append(f"{head} :- {input_constraints}.")
    param_to_type = {p: t for p, t in zip(dp.params, dp.types)}
    print("param to type: ", param_to_type)
    if prefix is None:
        prefix = dp.name
    new_dp_lines, new_lines = dp_formula_to_clingo(
        param_to_type, derived_predicate, prefix, trigger_type, dp.body, counter
    )
    lines += new_lines
    lines.append(
        f"postcondition({derived_predicate}, type({trigger_type}), effect(unconditional), {derived_var}, value({derived_var}, true)) :- {head}."
    )

    return new_dp_lines, lines


def make_dp_precondition(
    dp_string: str,
    trigger_type: str,
    var: str,
    val: str,
    extra_constraints: list[str] = None,
):
    if extra_constraints is not None:
        constraints_str = " : " + ", ".join(extra_constraints)
    else:
        constraints_str = ""
    return [
        f"precondition({dp_string}, type({trigger_type}), {var}, value({var}, {val})) {constraints_str} :- derivedPredicate({dp_string}, type({trigger_type}))."
    ]


def dp_formula_to_clingo(
    param_to_type: dict[oml.Symbol, str],
    dp_string: str,
    intermediate_prefix: str,
    trigger_type: str,
    formula,
    counter: list[int],
):
    print(dp_string, type(formula))
    match formula:
        case Fact() | NegatedFact():
            if isinstance(formula, Fact):
                val = "true"
            else:
                val = "false"
            parms = ", ".join(variable_to_clingo(p) for p in formula.body)
            var = f'variable(("{formula.head}", {parms}))'
            new_og_lines = make_dp_precondition(dp_string, trigger_type, var, val)

            return [], new_og_lines

        case Conjunction() | Disjunction():
            if (isinstance(formula, Conjunction) and trigger_type == "and") or (
                isinstance(formula, Disjunction) and trigger_type == "or"
            ):
                new_intermediate_lines = []
                new_og_lines = []
                print("conjunction clauses: ", formula.clauses)
                for c in formula.clauses:
                    if isinstance(c, oml.Bool):
                        continue
                    new_int, new_og = dp_formula_to_clingo(
                        param_to_type,
                        dp_string,
                        intermediate_prefix,
                        trigger_type,
                        c,
                        counter,
                    )
                    new_intermediate_lines += new_int
                    new_og_lines += new_og

                print("returning new_intermediate lines: ", new_intermediate_lines)
                return new_intermediate_lines, new_og_lines
            else:
                params = formula.get_params_matching(
                    lambda x: isinstance(x, oml.Symbol)
                    and (x.identifier.startswith("?") or x.identifier.startswith("&"))
                )
                params = list(set(params))
                types = [param_to_type[p] for p in params]
                idx = counter[0]
                counter[0] += 1
                derived_var = f"intermediate{idx}"
                new_dp = oml.DerivedPredicate(
                    derived_var, params, types, formula, counter
                )

                parm_str = ", ".join(variable_to_clingo(p) for p in params)
                derived_var_str = f'variable(("{derived_var}", {parm_str}))'

                int_int, og_int = derived_predicate_to_clingo(
                    new_dp, counter, intermediate_prefix
                )
                new_intermediate_lines = int_int + og_int
                new_og_lines = make_dp_precondition(
                    dp_string, trigger_type, derived_var_str, "true"
                )
                print("2returning new_intermediate lines: ", new_intermediate_lines)
                return new_intermediate_lines, new_og_lines

        case UniversalQuantifier():
            # Turn "forall x, f(x)" into "not (exists x (not (f x)))"

            domain = formula.domain

            if isinstance(formula.body, oml.Implication):
                print("implication body: ", formula)
                # domain += formula.body.head
                domain = Conjunction([domain, formula.body.head])
                body = Negation(formula.body.body)
            else:
                body = Negation(formula.body)

            idx = counter[0]
            counter[0] += 1
            derived_var = f"intermediate{idx}"
            inverted_formula = ExistentialQuantifier(
                formula.formal_params, formula.param_types, body, domain
            )
            parm_str = ", ".join(variable_to_clingo(p) for p in param_to_type)
            derived_var_str = f'variable(("{derived_var}", {parm_str}))'

            new_dp = oml.DerivedPredicate(
                derived_var,
                list(param_to_type.keys()),
                list(param_to_type.values()),
                inverted_formula,
            )

            int_int, og_int = derived_predicate_to_clingo(
                new_dp, counter, intermediate_prefix
            )
            new_intermediate_lines = int_int + og_int

            new_og_lines = make_dp_precondition(
                dp_string, trigger_type, derived_var_str, "false"
            )
            print("3returning new_intermediate lines: ", new_intermediate_lines)
            return new_intermediate_lines, new_og_lines

        case ExistentialQuantifier():
            params = formula.get_params_matching(
                lambda x: isinstance(x, oml.Symbol)
                and (x.identifier.startswith("?") or x.identifier.startswith("&"))
            )
            params = list(set(params))
            for p, t in zip(formula.formal_params, formula.param_types):
                param_to_type[p] = t
            # NOTE: this param logic probably isn't quite right for more deeply nested clauses
            # Specifically, we want to skip lifted params that are introduced by descendant quantified expressions.

            # TODO: For the set of params we choose, we need to tell this
            # to the caller so that the correct parameters for the
            # derivedPredicate can be set

            types = [param_to_type[p] for p in params]

            # extra_constraints = []
            # for var, t in zip(formula.formal_params, formula.param_types):
            #    extra_constraints.append(f'has({variable_to_clingo(var)}, type("{t}"))')
            #    extra_constraints.append(f"inworld({variable_to_clingo(var)})")

            idx = counter[0]
            counter[0] += 1
            derived_var = f"intermediate{idx}"
            parm_str = ", ".join(variable_to_clingo(p) for p in params)
            derived_var_str = f'variable(("{derived_var}", {parm_str}))'

            new_formula = Conjunction([formula.domain, formula.body])
            new_dp = oml.DerivedPredicate(derived_var, params, types, new_formula)

            int_int, og_int = derived_predicate_to_clingo(
                new_dp, counter, intermediate_prefix
            )
            new_intermediate_lines = int_int + og_int

            new_og_lines = make_dp_precondition(
                dp_string,
                trigger_type,
                derived_var_str,
                "false",
                extra_constraints=extra_constraints,
            )

            print("4returning new_intermediate lines: ", new_intermediate_lines)
            return new_intermediate_lines, new_og_lines

        case Negation():
            match formula.clause:
                case Fact() | NegatedFact():
                    # If the body is a fact, then generate precondition for negated fact.
                    x, new_og_lines = dp_formula_to_clingo(
                        param_to_type,
                        dp_string,
                        intermediate_prefix,
                        trigger_type,
                        oml.negate(formula.clause),
                        counter,
                    )
                    assert (
                        x == []
                    )  # shouldn't be any new derived predicates because we know it's a Fact
                    return [], new_og_lines
                case _:
                    # Otherwise, negate the output of an intermediate stream.
                    params = formula.get_params_matching(
                        lambda x: isinstance(x, oml.Symbol)
                        and (
                            x.identifier.startswith("?") or x.identifier.startswith("&")
                        )
                    )
                    params = list(set(params))
                    types = [param_to_type[p] for p in params]

                    idx = counter[0]
                    counter[0] += 1
                    derived_var = f"intermediate{idx}"
                    parm_str = ", ".join(variable_to_clingo(p) for p in params)
                    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

                    new_dp = oml.DerivedPredicate(
                        derived_var, params, types, formula.clause
                    )

                    int_int, og_int = derived_predicate_to_clingo(
                        new_dp, counter, intermediate_prefix
                    )
                    new_intermediate_lines = int_int + og_int

                    new_og_lines = make_dp_precondition(
                        dp_string, trigger_type, derived_var_str, "false"
                    )

                    return new_intermediate_lines, new_og_lines
        case _:
            raise Exception(
                f"Don't know how to handle {formula} in derived predicate condition"
            )


def generate_optimization_clingo(
    domain: FullDomain, env: Environment, problem: Problem
):
    # Currently, generate a plan in the "maximally feasible world"
    return ["#maximize {1, X : inworld(X)}."]


def generate_show_init_state_clingo():
    helper = "trueInitialState(Var) :- initialState(Var, value(Var, true))."
    show = "#show trueInitialState/1."
    return [helper, show]


def get_typed_groups(env: Environment, state: oml.State) -> dict[str, str]:
    id_to_type = {}
    for f in state.facts:
        if f.head == "group":
            group_symbol = f.body[0]
            group_type = env.get_metadata_for_symbol(group_symbol).get(
                "group_type", "object"
            )
            id_to_type[group_symbol.identifier] = group_type
    return id_to_type


def generate_group_types(domain: FullDomain, env: Environment, problem: Problem):
    clingo = []

    clingo.append(
        "has(X, grouptype(T2)) :- has(X, grouptype(T1)), inherits(type(T1), type(T2))."
    )
    group_to_type = get_typed_groups(env, problem.initial_state)
    for group, type in group_to_type.items():
        clingo.append(f'has(constant("{group}"), grouptype("{type}")).')
        clingo.append(f'is(constant("{group}"), grouptype("{type}")).')

    return clingo


def to_clingo_type_string(var, type):
    return f'has({var}, type("{type}"))'


def to_clingo_group_type_string(var, type):
    return f'has({var}, grouptype("{type}"))'


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
        maybe_inworld = f'{{inworld(constant("{sid}"))}}.'
        clingo_lines += [decl, typed, fromstream, maybe_inworld]
    inworld_is_caused = ":- inworld(O), fromstream(O), not generated(O)."
    clingo_lines.append(inworld_is_caused)
    return clingo_lines


def to_lifted_clingo_string(fact: Fact):
    head = fact.head.replace("-", "_")
    return f"{head}({', '.join([variable_to_clingo(p) for p in fact.body])})"


def to_clingo_string(fact: Fact):
    head = fact.head.replace("-", "_")
    body = ", ".join([f'constant("{p.identifier}")' for p in fact.body])
    return f"{head}({body})"


def variable_to_clingo(symbol: oml.Symbol) -> str:
    s = symbol.identifier.upper()
    if s.startswith("?") or s.startswith("&"):
        s = s[1:]
    return s


def stream_to_clingo(stream: Stream):
    """Represent each stream, constraining its input and possible outputs"""
    formal_args = tuple(variable_to_clingo(s) for s in stream.formal_params)
    formal_outputs = tuple(variable_to_clingo(s) for s in stream.formal_outputs)

    formal_args_str = ", ".join((f'"{stream.name}"',) + formal_args + formal_outputs)

    # {Chosen(stream(θ))} ← θ ∈ Dom(stream; ˆW )

    output_type_restrictions = []
    for p, r in zip(stream.formal_outputs, stream.output_restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one output (type) restriction for streams. Stream {stream.name} has output {p} with restrictions {r}"
            )
        output_type_restrictions.append(
            to_clingo_type_string(variable_to_clingo(p), r[0])
        )
        output_type_restrictions.append(f"fromstream({variable_to_clingo(p)})")
    output_type_restrictions_str = ", ".join(output_type_restrictions)

    input_type_restrictions = []
    input_realization_constraints = []
    for p, r in zip(stream.formal_params, stream.restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one input (type) restriction for streams. Stream {stream.name} has input {p} with restrictions {r}"
            )
        input_type_restrictions.append(
            to_clingo_type_string(variable_to_clingo(p), r[0])
        )
        input_realization_constraints.append(f"inworld({variable_to_clingo(p)})")

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
    generation_constraint = f"""{{stream_generated(({formal_args_str})) : {output_type_restrictions_str}}} <= {max_generations} :- {stream_applicability_constraint}."""

    stream_clingo = [generation_constraint]

    # Stream consistency
    for p in stream.formal_outputs:
        stream_clingo.append(
            f"""generated_by({variable_to_clingo(p)}, ({formal_args_str})) :- stream_generated(({formal_args_str}))."""
        )
        stream_clingo.append(
            f"generated({variable_to_clingo(p)}) :- stream_generated(({formal_args_str}))."
        )
    # generated_by(formal, (formal_args_str)) :- stream_generated(formal_args_str).

    # f ∈ Wstream ← f ∈ Certified(stream), Chosen(stream)
    for fact in stream.certificates:
        predicate = f'"{fact.head}"'
        fact_body = tuple(variable_to_clingo(s) for s in fact.body)

        initial_state = "true"
        lifted_fact = (predicate,) + fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        clause = f"""initialState({var}, value({var}, {initial_state})) :- stream_generated(({formal_args_str}))."""
        stream_clingo.append(clause)

        fact_str = to_lifted_clingo_string(fact)
        static_clause = f"""{fact_str} :- stream_generated(({formal_args_str}))."""
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
                to_clingo_type_string(variable_to_clingo(p), r[0])
            )
            input_realization_constraints.append(f"inworld({variable_to_clingo(p)})")

        domain_constraints = []
        for f in df.domain:
            if isinstance(f, Fact):
                domain_constraints.append(to_lifted_clingo_string(f))
            elif isinstance(f, NegatedFact):
                domain_constraints.append(f"not {to_lifted_clingo_string(f)}")

        stream_applicability_constraint = ", ".join(
            input_type_restrictions + input_realization_constraints + domain_constraints
        )

        formal_args = tuple(variable_to_clingo(s) for s in df.formal_params)
        formal_args_str = ", ".join((f'"{df.name}"',) + formal_args)
        stream_derived = f"""stream_derived({formal_args_str}) :- {stream_applicability_constraint}."""
        output_clingo.append(stream_derived)
        for cert in df.certificates:
            predicate = f'"{cert.head}"'
            fact_body = tuple(variable_to_clingo(s) for s in cert.body)
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
    action_list = [f'"{action.name}"'] + [variable_to_clingo(p) for p in action.params]
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

        if is_group_param(p):
            input_type_restrictions.append(
                to_clingo_group_type_string(variable_to_clingo(p), r[0])
            )
            input_group_constraints.append(f"group({variable_to_clingo(p)})")
        else:
            input_type_restrictions.append(
                to_clingo_type_string(variable_to_clingo(p), r[0])
            )

        input_realization_constraints.append(f"inworld({variable_to_clingo(p)})")

    action_applicability_constraint = ", ".join(
        input_type_restrictions
        + input_realization_constraints
        + input_group_constraints
    )
    clingo_lines = [f"action({action_header}) :- {action_applicability_constraint}."]

    for constraint in action.precondition:
        predicate = f'"{constraint.head}"'
        if isinstance(constraint, oml.Fact):
            condition = "true"
        else:
            assert isinstance(constraint, oml.NegatedFact)
            condition = "false"

        lifted_fact_body = [variable_to_clingo(s) for s in constraint.body]

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        requirements_str = ", ".join(requirements)
        clingo_lines.append(
            f"precondition({action_header}, {var}, value({var}, {condition})) :- {requirements_str}."
        )

    for constraint in action.positive_effect:
        predicate = f'"{constraint.head}"'

        lifted_fact_body = [variable_to_clingo(s) for s in constraint.body]

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        requirements_str = ", ".join(requirements)

        clingo_lines.append(
            f"postcondition({action_header}, effect(unconditional), {var}, value({var}, true)) :- {requirements_str}."
        )
    for constraint in action.negative_effect:
        predicate = f'"{constraint.head}"'

        lifted_fact_body = [variable_to_clingo(s) for s in constraint.body]

        lifted_fact = [predicate] + lifted_fact_body
        lifted_fact_str = ", ".join(lifted_fact)
        var = f"""variable(({lifted_fact_str}))"""

        requirements = [f"action({action_header})"]
        requirements_str = ", ".join(requirements)
        clingo_lines.append(
            f"postcondition({action_header}, effect(unconditional), {var}, value({var}, false)) :- {requirements_str}."
        )

    return clingo_lines


def generate_groupable_predicates(
    domain: FullDomain, env: Environment, problem: Problem
):
    predicates = ["visited", "observed"]
    lines = [f'groupable_predicate("{p}").' for p in predicates]
    return lines


def generate_group_action_clingo(domain: FullDomain):
    clingo_lines = [
        """
{ingroup(X, Y)} :- group(X), is(X, grouptype(T)), has(Y, type(T)), not group(Y).
inworld(Y) :- group(X), ingroup(X, Y), inworld(X).
:- inworld(X), fromstream(X), not generated(X).
#show generated_by/2.
    """
    ]
    #:- inworld(X), fromstream(X), stream_generated(Stream), not generated_by(X, Stream).
    for action in domain.pddl_domain.group_actions:
        clingo_lines += group_action_to_clingo(action)

    clingo_lines.append("#show ingroup/2.")

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

    if incremental:
        output_clingo += ["#program bsp_restriction."]
    # Necessary to enforce that the span of the belief state is contained within the goal.
    output_clingo += [":- goal(Variable, Value), holds(Variable, Value, 0)."]

    n_string_args = set(len(s.formal_params) + len(s.formal_outputs) for s in streams)
    for n in n_string_args:
        output_clingo += ["#show inworld/1."]

    output_clingo.append("#show stream_generated/1.")

    return output_clingo
