# ruff: noqa: F811
from __future__ import annotations
from dataclasses import dataclass, field
from omnilang.environment import Symbol
from omnilang.mdp_states import Fact, NegatedFact
from plum import dispatch


@dataclass
class Bool:
    value: bool

    def __str__(self):
        return str(self.value)

    def get_params_matching(self, f):
        return []

    def get_quantified_variables(self):
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

    def get_quantified_variables(self):
        qvars = []
        for c in self.clauses:
            qvars += c.get_quantified_variables()
        return qvars


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

    def get_quantified_variables(self):
        qvars = []
        for c in self.clauses:
            qvars += c.get_quantified_variables()
        return qvars


@dataclass
class Negation:
    clause: Formula

    def __str__(self):
        return "(not " + str(self.clause) + ")"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.clause.get_params_matching(f)

    def get_quantified_variables(self):
        return self.clause.get_quantified_variables()


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

    def get_quantified_variables(self):
        return (
            self.head.get_quantified_variables() + self.body.get_quantified_variables()
        )


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
        if self.domain == Bool(True):
            return f"(forall ({head_str}) {self.body.to_pddl_string()})"
        else:
            return f"(forall ({head_str}) ({self.domain}) {self.body.to_pddl_string()})"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.domain.get_params_matching(f) + self.body.get_params_matching(f)

    def get_quantified_variables(self):
        return (
            self.formal_params
            + self.body.get_quantified_variables()
            + self.domain.get_quantified_variables()
        )


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
        if self.domain == Bool(True):
            return f"(exists ({head_str}) {self.body.to_pddl_string()})"
        else:
            return f"(exists ({head_str}) ({self.domain}) {self.body.to_pddl_string()})"

    def to_pddl_string(self):
        return str(self)

    def get_params_matching(self, f):
        return self.domain.get_params_matching(f) + self.body.get_params_matching(f)

    def get_quantified_variables(self):
        return (
            self.formal_params
            + self.body.get_quantified_variables()
            + self.domain.get_quantified_variables()
        )


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


@dispatch
def simplify(formula):
    return formula


@dispatch
def simplify(formula: ExistentialQuantifier | UniversalQuantifier):
    return type(formula)(
        formula.formal_params,
        formula.param_types,
        simplify(formula.body),
        simplify(formula.domain),
    )


@dispatch
def simplify(formula: Conjunction):
    formula = Conjunction([simplify(c) for c in formula.clauses])

    has_false = any(c == Bool(False) for c in formula.clauses)
    if has_false:
        return Bool(False)
    updated_clauses = [c for c in formula.clauses if c != Bool(True)]
    if len(updated_clauses) > 1:
        return Conjunction(updated_clauses)
    elif len(updated_clauses) == 1:
        return updated_clauses[0]
    return Bool(True)


@dispatch
def simplify(formula: Disjunction):
    formula = Disjunction([simplify(c) for c in formula.clauses])
    has_true = any(c == Bool(True) for c in formula.clauses)
    if has_true:
        return Bool(True)
    updated_clauses = [c for c in formula.clauses if c != Bool(False)]
    if len(updated_clauses) > 1:
        return Disjunction(updated_clauses)
    elif len(updated_clauses) == 1:
        return updated_clauses[0]
    return Bool(False)
