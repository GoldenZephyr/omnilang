# ruff: noqa: F811
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from plum import dispatch


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

    def __post_init__(self):
        assert isinstance(self.identifier, str)

    def __str__(self):
        return f"sym-{self.identifier}"

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
        return f"({self.head + ' ' + ' '.join([p.identifier for p in self.body])})"

    def __str__(self):
        return f"({self.head} {' '.join(str(b) for b in self.body)})"


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

    def __str__(self):
        return f'State({", ".join(str(f) for f in self.facts)})'

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

    def __str__(self):
        return f"PartialState({' '.join([str(f) for f in self.positive_facts]
                + [str(negate(f)) for f in self.negative_facts])})"


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
    base_improper_quantified_set: Optional[ImproperQuantifiedSet] = None


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


def exists(unbound_element: str, element_type_restriction: str, fact_template):
    if element_type_restriction is None:

        def filt(env, x):
            return True
    elif isinstance(element_type_restriction, str):

        def filt(env, x):
            return env.get_object_type(x) == element_type_restriction
    else:
        raise Exception(
            f"element_type_restriction must be string or None, not {type(element_type_restriction)}"
        )

    def fill_in_fact(env, x):  # TODO: probably need this for forall too
        parms = []
        for p in fact_template.body:
            if p.identifier == unbound_element:
                parms.append(x)
            else:
                parms.append(p)
        return Fact(fact_template.head, parms)

    return ImproperQuantifiedSet(
        "exists",
        [unbound_element],
        None,
        filt,
        fill_in_fact,
    )


@dataclass
class PddlExists:
    unbound_elements: list[Symbol]
    type_restrictions: list[str]
    body: list[Fact]  # implicitly conjunction


@dataclass
class PddlForall:
    unbound_elements: list[Symbol]
    type_restrictions: list[str]
    body: list[Fact]  # implicitly conjunction


# def pddl_exists(unbound_elements: list[str], type_restrictions: list[str], quantifier_body):
#    pass
