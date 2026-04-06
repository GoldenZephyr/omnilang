from dataclasses import dataclass
from omnilang.mdp_states import Fact, Symbol
from omnilang.mdp_actions import LiftedAction
from typing import Optional
from omnilang.utils import indent
from typing import Any
from omnilang.logical_clauses import Formula


@dataclass(frozen=True)
class PddlProblemInstance:
    name: str
    domain: str
    objects: list[Symbol]
    objects_to_type: dict[Symbol, str]
    type_to_objects: dict[str, list[Symbol]]
    initial_facts: list[Fact]
    goal: Any  # TODO: refine


@dataclass(frozen=True)
class DomainPredicate(Fact):
    type_restrictions: list[list[str]]

    def to_pddl_string(self):
        parm_strings = []
        for parm, types in zip(self.body, self.type_restrictions):
            match types:
                case []:
                    parm_strings.append(f"{parm.identifier} - object")
                case [t]:
                    parm_strings.append(f"{parm.identifier} - {t}")
                case _:
                    raise Exception(
                        f"PDDL domain predicates only support a single type restriction. {self.head} {parm} was given: {types}"
                    )
        return "(" + self.head + " " + " ".join(parm_strings) + ")"


@dataclass
class DerivedPredicate:
    name: str
    params: list[Symbol]
    types: list[str]
    body: Formula


@dataclass
class PddlDomain:
    name: str
    types: dict[str, list[str]]
    functions: Optional[list]  # NOTE: we don't support functions yet
    predicates: list[DomainPredicate]
    actions: list[LiftedAction]
    requirements: Optional[list[str]] = None
    group_actions: Optional[list[LiftedAction]] = None
    derived_predicates: Optional[list[DerivedPredicate]] = None

    def __post_init__(self):
        self.names_to_action = {a.name: a for a in self.actions}
        self.type_to_parent = {}
        for supertype, subtypes in self.types.items():
            for st in subtypes:
                self.type_to_parent[st] = supertype

    def to_string(self, include_group_actions=False, include_derived_predicates=False):
        lines = [(f"(define (domain {self.name})")]

        if self.requirements is not None:
            lines += indent(1, self._requirements_block_pddl_str())

        if self.types is not None:
            lines += indent(1, self._types_block_pddl_str())

        if self.functions is not None:
            lines.append(indent(1, "(:functions )"))

        lines += indent(1, self._predicates_block_pddl_str())

        if include_derived_predicates:
            lines += indent(1, self._derived_predicates_block_pddl_str())

        for action in self.actions:
            lines += indent(1, action.to_pddl_lines())

        if include_group_actions and self.group_actions is not None:
            for action in self.group_actions:
                lines += indent(1, action.to_pddl_lines())

        lines.append(")")
        return "\n".join(lines)

    def _requirements_block_pddl_str(self):
        req_string = " ".join(f":{r}" for r in self.requirements)
        return [f"(:requirements {req_string})"]

    def _types_block_pddl_str(self):
        lines = ["(:types"]
        for parent_type, children_types in self.types.items():
            lines.append(indent(1, " ".join(children_types) + " - " + parent_type))
        lines.append(")")
        return lines

    def _predicates_block_pddl_str(self):
        lines = ["(:predicates"]
        for p in self.predicates:
            lines.append(indent(1, p.to_pddl_string()))
        lines.append(")")
        return lines

    def _derived_predicates_block_pddl_str(self):
        lines = []
        for dp in self.derived_predicates:
            parms_str = " ".join(p.identifier for p in dp.params)
            lines.append(f"(:derived ({dp.name} {parms_str})")
            lines.append(indent(1, dp.body.to_pddl_string()))
            lines.append(")")
            return lines

    def get_action(self, action_name):
        return self.names_to_action.get(action_name, None)

    def get_group_types(self):
        if self.group_actions is None:
            return None
        types = []
        for ga in self.group_actions:
            for parm, type in zip(ga.params, ga.param_restrictions):
                if parm.identifier.startswith("&"):
                    types.append(type[0])
        return types

    def add_derived_predicate_types(self):
        name_to_predicate = {p.head: p for p in self.predicates}
        for dp in self.derived_predicates:
            if dp.name in name_to_predicate:
                pred = name_to_predicate[dp.name]
                types = [t[0] for t in pred.type_restrictions]
            else:
                print("Warning: derived predicate {dp.name} not listed in predicates!")
                types = ["object"] * len(dp.params)
            dp.types = types


if __name__ == "__main__":
    from parse_mdp import parse_domain_file

    domain = parse_domain_file("move_action_test.pddl")
    print(domain.to_pddl_string())
