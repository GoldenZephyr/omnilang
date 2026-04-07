import omnilang as oml
from omnilang import Fact, NegatedFact
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    variable_to_clingo,
    to_clingo_type_string,
    to_w0_constraint,
)


def generate_derived_certificate(kernel: str, certificate: oml.Fact | oml.NegatedFact):
    # predicate = f'"{certificate.head}"'
    # fact_body = tuple(variable_to_clingo(s) for s in certificate.body)

    # lifted_fact = (predicate,) + fact_body
    # lifted_fact_str = ", ".join(lifted_fact)
    # var = f"""variable(({lifted_fact_str}))"""

    # initialState = f"""initialState({var}, value({var}, {initial_state})) :- stream_derived({kernel})."""
    # lines = [initialState]

    fact_str = to_w0_constraint(certificate)
    match certificate:
        case oml.Fact():
            static_fact = f"{fact_str} :- stream_derived({kernel})."
        case oml.NegatedFact():
            static_fact = f"-{fact_str} :- stream_derived({kernel})."
        case _:
            raise Exception(f"Unknown thing being certified: {certificate}")
    lines = [static_fact]
    return lines


def generate_derived_stream_applicability(stream):
    lines = []
    for p, r in zip(stream.formal_params, stream.restrictions):
        if len(r) != 1:
            raise Exception(
                f"Currently only support one input (type) restriction for streams. Stream {stream.name} has input {p} with restrictions {r}"
            )
        lines.append(to_clingo_type_string(variable_to_clingo(p), r[0]))
        lines.append(f"inworld({variable_to_clingo(p)})")

    for f in stream.domain:
        if isinstance(f, Fact):
            lines.append(to_w0_constraint(f))
        elif isinstance(f, NegatedFact):
            lines.append(f"not {to_w0_constraint(f)}")
    return lines


def generate_derived_stream(stream: oml.DerivedStreamFacts):
    lines = []

    input_constraints = generate_derived_stream_applicability(stream)
    stream_applicability_constraint = ", ".join(input_constraints)

    formal_args = tuple(variable_to_clingo(s) for s in stream.formal_params)
    kernel_str = ", ".join((f'"{stream.name}"',) + formal_args)
    stream_derived = (
        f"""stream_derived({kernel_str}) :- {stream_applicability_constraint}."""
    )
    lines.append(stream_derived)
    for cert in stream.certificates:
        lines += generate_derived_certificate(kernel_str, cert)
    return lines


def compile_derived_streams(env, domain: oml.FullDomain, state):
    """Support "derived streams" that add additional static facts"""
    # head(B1, ..., BN) :- type restrictions, domain.
    # initialState(variable(head(B1, ..., BN)), value(variable((head(B1,...,BN))), true)) :- type restrictions, domain.
    lines = ["% Derived Streams"]
    for df in domain.derived_stream_facts:
        lines += generate_derived_stream(df)
        lines[-1] += "\n"

    return lines
