from dataclasses import dataclass
from omnilang.mdp_states import Predicate, Fact
from omnilang.mdp_actions import LiftedAction
from typing import Optional
from omnilang.utils import indent


@dataclass
class PddlDomain:
    name: str
    types: Optional[list[Predicate]]  # NOTE: wrong type?
    functions: Optional[list]  # NOTE: we don't support functions yet
    predicates: list[Fact]
    actions: list[LiftedAction]

    def __post_init__(self):
        self.names_to_action = {a.name: a for a in self.actions}

    def to_pddl_string(self):
        lines = [(f"(define (domain {self.name})")]

        if self.types is not None:
            lines += indent(1, self._types_block_pddl_str())

        if self.functions is not None:
            lines.append(indent(1, "(:functions )"))

        lines += indent(1, self._predicates_block_pddl_str())

        for action in self.actions:
            lines += indent(1, action.to_pddl_lines())

        lines.append(")")
        print("lines: ", lines)
        return "\n".join(lines)

    def _types_block_pddl_str(self):
        lines = ["(:types"]
        for parent_type, children_types in self.types.items():
            lines.append(indent(1, " ".join(children_types) + " - " + parent_type))
        lines.append(")")
        return lines

    def _predicates_block_pddl_str(self):
        lines = ["(:predicates"]
        for p in self.predicates:
            pred = (
                "(" + p.head + " " + " ".join(map(lambda x: x.identifier, p.body)) + ")"
            )
            lines.append(indent(1, pred))
        lines.append(")")
        return lines

    def get_action(self, action_name):
        return self.names_to_action.get(action_name, None)


if __name__ == "__main__":
    from parse_mdp import parse_domain_file

    domain = parse_domain_file("move_action_test.pddl")
    print(domain.to_pddl_string())
