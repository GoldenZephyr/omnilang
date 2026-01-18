# ruff: noqa: F811
from __future__ import annotations
from dataclasses import dataclass
import copy
from typing import Optional
from functools import partial
from plum import dispatch


@dataclass
class Environment:
    parent_environment: Optional[Environment]
    symbols: list
    symbol_to_type: dict

    def get_object_type(self, o):
        if o in self.symbol_to_type:
            return self.symbol_to_type[o]
        else:
            if self.parent_environment is not None:
                return self.parent_environment.get_object_type(o)
            print(f"WARNING: No type for symbol {o}")
            return None


class Restriction:
    pass


@dataclass
class Predicate:
    head: str
    n_params: int
    param_restrictions: list[list[Restriction]]


@dataclass
class Symbol:
    identifier: str

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.identifier == other.identifier
        return self.identifier == other
        # return NotImplemented


@dataclass
class TypedSymbol:
    identifier: str
    type: str


@dataclass
class SymbolGenerator:
    identifier: str
    restrictions: list[Restriction]


@dataclass(frozen=True)
class Fact:
    head: str
    body: list[Symbol | SymbolGenerator]

    def to_tuple(self):
        return (self.head, *[b.identifier for b in self.body])

    def __hash__(self):
        return hash(self.to_tuple())

    def __eq__(self, other):
        if isinstance(other, Fact):
            return hash(self) == hash(other)
        return NotImplemented

    def to_pddl_string(self):
        return f"({self.head + " " + ' '.join([p.identifier for p in self.body])})"


@dataclass(frozen=True)
class NegatedFact:
    head: str
    body: list[Symbol | SymbolGenerator]

    def to_tuple(self):
        return (self.head, *[b.identifier for b in self.body])

    def __hash__(self):
        return hash(self.to_tuple())

    def __eq__(self, other):
        if isinstance(other, Fact):
            return hash(self) == hash(other)
        return NotImplemented

    def to_pddl_string(self):
        return f"(not {negate(self).to_pddl_string()})"


@dispatch
def negate(fact: Fact):
    return NegatedFact(fact.head, fact.body)


@dispatch
def negate(fact: NegatedFact):
    return Fact(fact.head, fact.body)


@dataclass
class State:
    facts: set[Fact]
    # implicitly assume facts that aren't listed are False

    def add_fact(self, fact):
        self.facts.add(fact)

    def remove_fact(self, fact):
        self.facts.remove(fact)

    def __contains__(self, e):
        match e:
            case Fact():
                return e in self.facts
            case State():
                return all(element in self.facts for element in e.facts)
            case PartialState():
                return all(
                    element in self.facts for element in e.positive_facts
                ) and all(element not in self.facts for element in e.negative_facts)
            case list():  # list of Facts (?)
                return all(element in self.facts for element in e)
            case _:
                raise NotImplementedError(
                    f"Cannot check containment for {type(e)} in {type(self)}"
                )


@dataclass
class PartialState:
    # When propagating a set of states through an action, we need to separately track unknown facts and negative facts
    positive_facts: set[Fact]
    negative_facts: set[Fact]


@dataclass
class StateGenerator:
    # A set of states is defined explicitly through a list of States or implicitly through the set of compatible bindings with Predicate
    # (TODO: really instead of Predicate we should have Clause, which might be a combination of Predicates)

    states: list[State | Predicate]


@dataclass
class QuantifiedSet:
    # TODO: The set-generation information here should be combined with Symbol generator or Predicate I think?
    quantifier: str  # exists or forall
    unbound_symbols: list[Symbol]
    domain: str  # TODO: what type? # Should this be called "generator"
    element_filter: callable  # x -> bool
    transformation: callable  # x -> y


@dataclass
class ImproperQuantifiedSet:
    quantifier: str  # exists or forall
    unbound_symbols: list[Symbol]
    domain: Optional[list]
    element_filter: callable  # environment, x -> bool
    transformation: callable  # environment, x -> y


def forall(unbound_element: str, element_type_restriction: str, fact_template):
    if element_type_restriction is None:

        def filt(env, x):
            return True
    elif isinstance(element_type_restriction, str):

        def filt(env, x):
            return env.get_object_type(x) == element_type_restriction

    return ImproperQuantifiedSet(
        "forall",
        [unbound_element],
        None,
        filt,
        lambda env, x: Fact(fact_template.head, [x]),
    )


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


def push(quantified_set: ImproperQuantifiedSet):
    """forall x (visited x) -> (visited (forall x x))"""
    qs = copy.deepcopy(quantified_set)
    qs.transformation = lambda env, x: x

    # TODO: this whole function probably needs to be parameterized by an
    # environment which is then passed here instead of None (?)
    return quantified_set.transformation(None, qs)


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
    return Fact(predicate.head, [binding[s] for s in predicate.body])
