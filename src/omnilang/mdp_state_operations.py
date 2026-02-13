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
)
from omnilang.environment import Environment


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


def satisfies(s, r):
    # TODO: use types to improve grounding efficiency
    return True


def iterate_satisfying_symbols(symbols, restrictions):
    for s in symbols:
        if satisfies(s, restrictions):
            yield s
    return


def ground(restrictions: list[list[Restriction]], symbols):
    if len(restrictions) == 0:
        yield []
    else:
        for s in iterate_satisfying_symbols(symbols, restrictions[0]):
            for binding in ground(restrictions[1:], symbols):
                yield [s] + binding


def ground_predicate(predicate, binding):
    match predicate:
        case Fact():
            constructor = Fact
        case NegatedFact():
            constructor = NegatedFact
        case _:
            constructor = Fact
    return constructor(predicate.head, [binding.get(s, s) for s in predicate.body])
