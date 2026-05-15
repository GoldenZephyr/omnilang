from omnilang import (
    Stream,
    Fact,
    NegatedFact,
)
import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    to_lifted_clingo_string,
    variable_to_clingo,
    to_clingo_type_string,
    to_w0_constraint,
)


def compile_stream_definitions(env, domain: oml.FullDomain, state):
    lines = ["% Streams"]

    for s in domain.streams:
        # Define each stream
        lines += stream_to_clingo(s)
        lines += ["\n"]
    # Ensure unique generation
    lines += make_general_stream_constraints()
    # Support derived streams
    # for ds in domain.derived_stream_facts:
    #     lines += derived_stream_to_clingo(ds)
    lines += [":- goal(Variable, Value), holds(Variable, Value, 0)."]
    return lines


def compile_stream_instances(env: oml.Environment, domain, state: oml.State):
    """Clingo boilerplate for each symbol that a stream might generate"""
    clingo_lines = ["% Stream-generated Variables"]
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

    return clingo_lines


def generate_stream_certificates(stream_kernel: str, certificates: list[oml.Fact]):
    lines = []
    for fact in certificates:
        # predicate = f'"{fact.head}"'
        # fact_body = tuple(variable_to_clingo(s) for s in fact.body)

        # initial_state = "true"
        # lifted_fact = (predicate,) + fact_body
        # lifted_fact_str = ", ".join(lifted_fact)
        # var = f"""variable(({lifted_fact_str}))"""

        # lines.append(
        #    f"""initialState({var}, value({var}, {initial_state})) :- stream_generated(({stream_kernel}))."""
        # )

        fact_str = to_w0_constraint(fact)
        match fact:
            case oml.Fact():
                return [f"""{fact_str} :- stream_generated(({stream_kernel}))."""]
            case oml.NegatedFact():
                return [f"""-{fact_str} :- stream_generated(({stream_kernel}))."""]
    return lines


def generate_stream_generation_tracking(
    stream_kernel: str, formal_outputs: list[oml.Symbol]
):
    lines = []
    for p in formal_outputs:
        lines.append(
            f"""generated_by({variable_to_clingo(p)}, ({stream_kernel})) :- stream_generated(({stream_kernel}))."""
        )
        lines.append(
            f"generated({variable_to_clingo(p)}) :- stream_generated(({stream_kernel}))."
        )
    return lines


def get_output_type_restrictions(stream):
    lines = []
    for p, r in zip(stream.formal_outputs, stream.output_restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one output (type) restriction for streams. Stream {stream.name} has output {p} with restrictions {r}"
            )
        lines.append(to_clingo_type_string(variable_to_clingo(p), r[0]))
        lines.append(f"fromstream({variable_to_clingo(p)})")
    return lines


def get_input_restrictions(stream):
    restrictions = []
    for p, r in zip(stream.formal_params, stream.restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one input (type) restriction for streams. Stream {stream.name} has input {p} with restrictions {r}"
            )
        restrictions.append(to_clingo_type_string(variable_to_clingo(p), r[0]))
        restrictions.append(f"inworld({variable_to_clingo(p)})")

    domain_constraints = []
    for f in stream.domain:
        if isinstance(f, Fact):
            domain_constraints.append(to_lifted_clingo_string(f))
        elif isinstance(f, NegatedFact):
            domain_constraints.append(f"not {to_lifted_clingo_string(f)}")

    return restrictions


def generate_generation_constraint(kernel: str, stream: oml.Stream):
    # {Chosen(stream(θ))} ← θ ∈ Dom(stream; ˆW )
    output_type_restrictions = get_output_type_restrictions(stream)
    output_type_restrictions_str = ", ".join(output_type_restrictions)

    restrictions = get_input_restrictions(stream)

    domain_constraints = []
    for f in stream.domain:
        if isinstance(f, Fact):
            domain_constraints.append(to_w0_constraint(f))
        elif isinstance(f, NegatedFact):
            domain_constraints.append(f"not {to_w0_constraint(f)}")
        else:
            raise TypeError(f"Unexpected stream domain element: {f}")

    stream_applicability_constraint = ", ".join(restrictions + domain_constraints)

    max_generations = 1
    generation_constraint = f"""{{stream_generated(({kernel})) : {output_type_restrictions_str}}} <= {max_generations} :- {stream_applicability_constraint}."""
    return [generation_constraint]


def stream_to_clingo(stream: Stream):
    """Represent each stream, constraining its input and possible outputs"""
    formal_args = tuple(variable_to_clingo(s) for s in stream.formal_params)
    formal_outputs = tuple(variable_to_clingo(s) for s in stream.formal_outputs)
    kernel_str = ", ".join((f'"{stream.name}"',) + formal_args + formal_outputs)

    # {Chosen(stream(θ))} ← θ ∈ Dom(stream; ˆW )
    lines = generate_generation_constraint(kernel_str, stream)

    # Track which stream generates which variable
    lines += generate_stream_generation_tracking(kernel_str, stream.formal_outputs)

    # f ∈ Wstream ← f ∈ Certified(stream), Chosen(stream)
    lines += generate_stream_certificates(kernel_str, stream.certificates)

    return lines


def make_general_stream_constraints():
    """Ensure that each symbol is only generated by one stream, and that we can track which possible symbols are "really" in the world"""
    # Stream consistency
    stream_consistency = ":- generated_by(X, Y), generated_by(X, Z), Y != Z."

    inworld_tracking = "inworld(X) :- generated_by(X, _)."
    inworld_default = 'inworld(X) :- not fromstream(X), has(X, type("object")).'
    group_inworld = "inworld(X) :- group(X)."
    inworld_is_caused = ":- inworld(O), fromstream(O), not generated(O)."

    clingo_lines = [
        "% Enforcing Stream Consistency",
        stream_consistency,
        inworld_tracking,
        inworld_default,
        group_inworld,
        inworld_is_caused,
    ]
    return clingo_lines
