# ruff: noqa: F811
from __future__ import annotations
from functools import partial
from plum import dispatch
from omnilang.mdp_states import (
    ImproperQuantifiedSet,
    QuantifiedSet,
    Fact,
    NegatedFact,
    Restriction,
    State,
)
from omnilang.environment import Environment, Symbol


def restrict(
    env: Environment, lifted_set: ImproperQuantifiedSet, symbol_to_restrict, domain
):
    unbound_symbols = [s for s in lifted_set.unbound_symbols if s != symbol_to_restrict]

    return QuantifiedSet(
        lifted_set.quantifier,
        unbound_symbols,
        domain,
        partial(lifted_set.element_filter, env),
        partial(lifted_set.transformation, env),
        base_improper_quantified_set=lifted_set,
    )


@dispatch
def push(qs: ImproperQuantifiedSet):
    """forall x (visited x) -> (visited (forall x x))"""
    # qs = copy.deepcopy(quantified_set)
    # qs = quantified_set
    # qs.transformation = lambda env, x: x

    quantified_set = ImproperQuantifiedSet(
        qs.quantifier,
        qs.unbound_symbols,
        qs.domain,
        qs.element_filter,
        lambda env, x: x,
    )

    return qs.transformation(None, quantified_set)


@dispatch
def push(qs: QuantifiedSet):
    """forall x (visited x) -> (visited (forall x x))"""
    # qs = copy.deepcopy(quantified_set)
    # qs = quantified_set
    # qs.transformation = lambda x: x

    quantified_set = QuantifiedSet(
        qs.quantifier,
        qs.unbound_symbols,
        qs.domain,
        qs.element_filter,
        lambda x: x,
        qs.base_improper_quantified_set,
    )

    return qs.transformation(quantified_set)


def generate(quantified_set: QuantifiedSet):
    for e in quantified_set.domain:
        if quantified_set.element_filter(e):
            yield quantified_set.transformation(e)


def iterate_satisfying_symbols(symbols, restrictions: list, env: Environment):
    if len(restrictions) == 0:
        # could be any symbol
        for s in symbols:
            yield s
    elif len(restrictions) == 1:
        possible_bindings = env.get_objects_of_type(restrictions[0])
        for s in possible_bindings:
            yield s
    else:
        raise Exception(
            f"Currently only support 0 or 1 restrictions, got {restrictions} instead"
        )
    return


def ground(restrictions: list[list[Restriction]], symbols, env=None):
    if len(restrictions) == 0:
        yield []
    else:
        for s in iterate_satisfying_symbols(symbols, restrictions[0], env):
            for binding in ground(restrictions[1:], symbols, env):
                yield [s] + binding


def is_bound_variable(var: Symbol):
    assert isinstance(var, Symbol)
    return not var.identifier.startswith("?")


def refine_potential_matches(
    state: State, domain: list[Fact], parm: Symbol, potential_matches
):
    for f in domain:
        try:
            idx = f.body.index(parm)
        except ValueError:
            continue

        relevant_facts = []
        for a in state.facts:
            if a.head != f.head:
                continue
            valid = True
            for ds, ss in zip(f.body, a.body):
                if is_bound_variable(ds) and ds != ss:
                    valid = False
            if valid:
                relevant_facts.append(a)
        matches_for_this = set(a.body[idx] for a in relevant_facts)
        potential_matches = potential_matches.intersection(matches_for_this)

    return potential_matches


def check_domain(state: State, domain: list[Fact | NegatedFact]):
    for f in domain:
        if not all(is_bound_variable(v) for v in f.body):
            continue
        match f:
            case Fact():
                if f not in state.facts:
                    return False
            case NegatedFact():
                if f in state.facts:
                    return False
    return True


def ground_with_domain_h(
    env: Environment,
    state: State,
    parm_to_symbols: list[tuple[Symbol, set[Symbol]]],
    domain: list[Fact | NegatedFact],
):
    if len(parm_to_symbols) == 0:
        yield []
    else:
        current_parm, possible_values = parm_to_symbols[0]
        rest = parm_to_symbols[1:]
        for s in possible_values:
            updated_domain = [ground_predicate(d, {current_parm: s}) for d in domain]
            # This enforces the domain for unary grounding, and also handles negative preconditions
            domain_ok = check_domain(state, updated_domain)
            if not domain_ok:
                continue

            restricted_bindings = [
                (m, refine_potential_matches(state, updated_domain, m, vals))
                for m, vals in rest
            ]
            invalid_binding = any(
                len(matches) == 0 for _, matches in restricted_bindings
            )
            if invalid_binding:
                continue

            for binding in ground_with_domain_h(
                env, state, restricted_bindings, updated_domain
            ):
                yield [s] + binding


def ground_with_domain(
    env: Environment,
    state: State,
    parms: list[Symbol],
    types: list[list[str]],
    domain: list[Fact],
):
    parm_to_symbols = []
    for p, t in zip(parms, types):
        values = set(env.get_objects_of_type(t[0]))
        parm_to_symbols.append((p, values))

    for grounding in ground_with_domain_h(env, state, parm_to_symbols, domain):
        yield grounding


def ground_predicate(predicate, binding):
    match predicate:
        case Fact():
            constructor = Fact
        case NegatedFact():
            constructor = NegatedFact
        case _:
            constructor = Fact
    return constructor(predicate.head, [binding.get(s, s) for s in predicate.body])
