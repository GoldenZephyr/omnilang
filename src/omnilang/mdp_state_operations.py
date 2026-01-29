# ruff: noqa: F811
from __future__ import annotations
import copy
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
    )


@dispatch
def push(quantified_set: ImproperQuantifiedSet):
    """forall x (visited x) -> (visited (forall x x))"""
    qs = copy.deepcopy(quantified_set)
    qs.transformation = lambda env, x: x

    # TODO: this whole function probably needs to be parameterized by an
    # environment which is then passed here instead of None (?)
    return quantified_set.transformation(None, qs)


@dispatch
def push(quantified_set: QuantifiedSet):
    """forall x (visited x) -> (visited (forall x x))"""
    qs = copy.deepcopy(quantified_set)
    qs.transformation = lambda x: x

    return quantified_set.transformation(qs)


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
