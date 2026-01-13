from __future__ import annotations
from dataclasses import dataclass
import copy
from typing import Optional
from functools import partial


# A Restriction is something that restricts the appplicable subset of symbols
# i.e. a type or predicate


@dataclass
class Environment:
    parent_environment: Optional[Environment]
    symbols: list
    symbol_to_type: dict

    def get_object_type(self, o):
        # TODO: if we fail the lookup, should check parent environment?
        if o in self.symbol_to_type:
            return self.symbol_to_type[o]
        else:
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
class SymbolGenerator:
    identifier: str
    restrictions: list[Restriction]


@dataclass
class Fact:
    head: str
    body: list[Symbol | SymbolGenerator]

    def to_tuple(self):
        return (self.head, *[b.identifier for b in self.body])


@dataclass
class State:
    facts: list[Fact]


@dataclass
class StateGenerator:
    # A set of states is defined explicitly through a list of States or implicitly through the set of compatible bindings with Predicate
    # (TODO: really instead of Predicate we should have Clause, which might be a combination of Predicates)

    states: list[State | Predicate]


# { g(x) | x \in S s.t. f(x) }


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


@dataclass
class LiftedAction:
    params: list[Symbol]
    param_restrictions: list[list[Restriction]]
    # TODO: I *think* that lifted actions should be thought of having ungrounded facts which are actually slightly different from predicates? And in that case, I'm not sure there's actually a distinction between Lifted and GroundedActions?
    precondition: list[Predicate]
    positive_effect: list[Predicate]
    negative_effect: list[Predicate]


@dataclass
class GroundedAction:
    precondition: list[Fact]
    positive_effect: list[Fact]
    negative_effect: list[Fact]


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


def bind_action(a, bindings):
    grounded_precondition = [ground_predicate(p, bindings) for p in a.precondition]
    grounded_positive_effects = [
        ground_predicate(p, bindings) for p in a.positive_effect
    ]
    grounded_negative_effects = [
        ground_predicate(p, bindings) for p in a.negative_effect
    ]
    return GroundedAction(
        grounded_precondition, grounded_positive_effects, grounded_negative_effects
    )


def ground_actions(actions: list[LiftedAction], symbols):
    # NOTE: probably need more information passed in to ensure that we can prevent binding symbols that don't meet the action restrictions

    for a in actions:
        r = {f: None for f in a.params}
        for bindings in ground(a.param_restrictions, symbols):
            for formal, val in zip(a.params, bindings):
                r[formal] = val

            ga = bind_action(a, r)
            yield ga


def compute_preimage(state, action):
    # Compute the preimage such that action(preimage) -> state

    # 1. Bind (lifted) effects to state
    # 2. evaluate preconditions for that value of formal parameters
    # 3. Add those preconditions to state, remove the effects from the state
    pass


goal = forall("p", "Place", Fact("visited", Symbol("p")))

print(push(goal))

env_symbols = [Symbol("p1"), Symbol("p2"), Symbol("p3")]
env_symbol_to_type = {}
env_symbol_to_type["p1"] = "Place"
env_symbol_to_type["p2"] = "Place"
env_symbol_to_type["p3"] = "Place"

goal = restrict(
    Environment(None, env_symbols, env_symbol_to_type), goal, "p", ["p1", "p2", "p3"]
)


for gs in generate(goal):
    print(gs)


move = LiftedAction(
    ["?p1", "?p2"],
    [[], []],
    [Fact("at", ["?p1"])],
    [Fact("at", ["?p2"])],
    [Fact("at", ["?p1"])],
)

actions = [move]
symbols = ["p1", "p2"]
for a in ground_actions(actions, symbols):
    print(a)
