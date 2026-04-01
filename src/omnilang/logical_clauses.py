from __future__ import annotations
from dataclasses import dataclass, field
from omnilang.environment import Symbol
from omnilang.mdp_states import Fact, NegatedFact


@dataclass
class Bool:
    value: bool

    def get_params_matching(self, f):
        return []


@dataclass
class Conjunction:
    clauses: list[Formula]

    def __str__(self):
        return "(and " + " ".join([str(e) for e in self.clauses]) + ")"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        params = []
        for c in self.clauses:
            params += c.get_params_matching(f)
        return params


@dataclass
class Disjunction:
    clauses: list[Formula]

    def __str__(self):
        return "(or " + " ".join([str(e) for e in self.clauses]) + ")"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        params = []
        for c in self.clauses:
            params += c.get_params_matching(f)
        return params


@dataclass
class Negation:
    clause: Formula

    def __str__(self):
        return "(not " + str(self.clause) + ")"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.clause.get_params_matching(f)


@dataclass
class Implication:
    head: Formula
    body: Formula

    def __str__(self):
        return f"(implies {self.head.to_pddl_string()} {self.body.to_pddl_string()})"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.head.get_params_matching(f) + self.body.get_params_matching(f)


@dataclass
class UniversalQuantifier:
    formal_params: list[Symbol]
    param_types: list[str]
    body: Formula
    domain: Formula = field(default_factory=lambda: Bool(True))

    def __str__(self):
        head_str = " ".join(
            f"{s} - {t}" for s, t in zip(self.formal_params, self.param_types)
        )
        return f"(forall {head_str} {self.body.to_pddl_string()})"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.domain.get_params_matching(f) + self.body.get_params_matching(f)


@dataclass
class ExistentialQuantifier:
    formal_params: list[Symbol]
    param_types: list[str]
    body: Formula
    domain: Formula = field(default_factory=lambda: Bool(True))

    def __str__(self):
        head_str = " ".join(
            f"{s} - {t}" for s, t in zip(self.formal_params, self.param_types)
        )
        return f"(exists {head_str} {self.body.to_pddl_string()})"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.domain.get_params_matching(f) + self.body.get_params_matching(f)


Formula = (
    Conjunction
    | Disjunction
    | Negation
    | Implication
    | UniversalQuantifier
    | ExistentialQuantifier
    | Fact
    | NegatedFact
    | Bool
)
