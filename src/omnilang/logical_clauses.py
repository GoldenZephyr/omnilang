from __future__ import annotations
from dataclasses import dataclass
from omnilang.mdp_states import Fact, NegatedFact


@dataclass
class Conjunction:
    clauses: list

    def __str__(self):
        return "(and " + " ".join([str(e) for e in self.clauses]) + ")"


@dataclass
class Disjunction:
    clauses: list

    def __str__(self):
        return "(or " + " ".join([str(e) for e in self.clauses]) + ")"


@dataclass
class Negation:
    clause: Conjunction | Negation | Fact | NegatedFact

    def __str__(self):
        return "(not " + str(self.clause) + ")"
