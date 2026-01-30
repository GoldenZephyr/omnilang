from __future__ import annotations
from importlib.resources import as_file, files
import omnilang.lark
from omnilang.mdp_states import (
    Fact,
    NegatedFact,
    negate,
    exists,
    forall,
    Symbol,
)
from lark import Lark, Transformer
from dataclasses import dataclass


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


class GoalTransformer(Transformer):
    def start(self, element):
        return element

    def element(self, items):
        return items[0]

    def atom(self, items):
        return Fact(str(items[0]), [Symbol(str(i)) for i in items[1:]])

    def negation(self, items):
        match items[0]:
            case Fact():
                return negate(items[1])
            case NegatedFact():
                return negate(items[1])
            case _:
                return Negation(items[1])

    def clause(self, items):
        return items[0]

    def disjunction(self, items):
        return Disjunction(items[1:])

    def conjunction(self, items):
        return Conjunction(items[1:])

    def quantified_clause(self, items):
        if len(items) == 3:
            quantifier, variable, body = items
            restriction = None
        elif len(items) == 4:
            quantifier, variable, restriction, body = items
        else:
            raise Exception(f"Invalid quantified clause: {items}")
        variable = str(variable)
        match str(quantifier):
            case "exists":
                quantifier_function = exists
            case "forall":
                quantifier_function = forall
            case _:
                raise ValueError(f"Unknown quantifier {quantifier}")

        # NOTE: currently our quantifiers take a single unary type restriction,
        # but eventually we could pass a more complex restriction (i.e.,
        # restriction instead of restriction.head. Currently arbitrary clauses
        # are valid in the CFG but won't transform successfully here.
        if restriction is not None:
            restriction = restriction.head
        return quantifier_function(Symbol(variable), restriction, body)

    def cname(self, items):
        return items[0]

    def restriction(self, items):
        return items[0]


def parse_goal_string(goal: str):
    with as_file(files(omnilang.lark).joinpath("pddl_goal.lark")) as path:
        with open(path, "r") as fo:
            goal_grammar = fo.read()

    goal_parser = Lark(
        goal_grammar,
    )

    T = GoalTransformer()

    tree = goal_parser.parse(goal)
    streams = T.transform(tree)
    return streams
