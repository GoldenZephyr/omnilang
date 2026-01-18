from dataclasses import dataclass
from omnilang.mdp_states import (
    PartialState,
    Restriction,
    Symbol,
    Fact,
    NegatedFact,
    ground_predicate,
    ground,
)
from omnilang.utils import indent


@dataclass
class LiftedAction:
    name: str
    params: list[Symbol]
    param_restrictions: list[list[Restriction]]

    # TODO: I *think* that lifted actions should be thought of having
    # ungrounded facts which are actually slightly different from predicates?
    # And in that case, I'm not sure there's actually a distinction between
    # Lifted and GroundedActions?

    precondition: (
        PartialState  # TODO: I think this should actually be a list of (lifted) facts?
    )
    positive_effect: list[Fact]
    negative_effect: list[Fact]

    def to_pddl_lines(self):
        lines = []
        lines.append(f"(:action {self.name}")

        str_params = " ".join([p.identifier for p in self.params])
        lines.append(indent(1, f":parameters ({str_params})"))

        lines += indent(1, self._precondition_pddl_str())

        lines += indent(1, self._effect_pddl_str())

        lines.append(")")
        return lines

    def _precondition_pddl_str(self):
        fact_lines = []
        for f in self.precondition:
            match f:
                case Fact():
                    fact_lines.append(f.to_pddl_string())
                case NegatedFact():
                    fact_lines.append("(not " + f.to_pddl_string() + ")")
                case _:
                    raise ValueError(f"Unknown precondition type: {f}")
        if len(fact_lines) == 0:
            return [":precondition ()"]
        elif len(fact_lines) == 1:
            return [f":precondition {fact_lines[0]}"]
        else:
            lines = [":precondition (and " + fact_lines[0]]
            lines += indent(5, fact_lines[1:])
            lines[-1] += ")"
            return lines

    def _effect_pddl_str(self):
        positive_fact_lines = [f.to_pddl_string() for f in self.positive_effect]
        negative_fact_lines = [
            "(not " + f.to_pddl_string() + ")" for f in self.negative_effect
        ]
        fact_lines = positive_fact_lines + negative_fact_lines
        if len(fact_lines) > 1:
            lines = [":effect (and " + fact_lines[0]]
            lines += indent(3, fact_lines[1:])
            lines[-1] += ")"
        else:
            lines = [":effect " + fact_lines[0]]

        return lines

    def to_pddl(self):
        return "\n".join(self.to_pddl_lines)


@dataclass
class GroundedAction:
    name: str
    precondition: list[Fact]
    positive_effect: list[Fact]
    negative_effect: list[Fact]


def bind_action(a, bindings):
    # NOTE: currently we only support positive preconditions (...)
    grounded_precondition = PartialState(
        [ground_predicate(p, bindings) for p in a.precondition], {}
    )
    grounded_positive_effects = [
        ground_predicate(p, bindings) for p in a.positive_effect
    ]
    grounded_negative_effects = [
        ground_predicate(p, bindings) for p in a.negative_effect
    ]
    return GroundedAction(
        a.name,
        grounded_precondition,
        grounded_positive_effects,
        grounded_negative_effects,
    )


def ground_actions(actions: list[LiftedAction], symbols):
    # NOTE: probably need more information passed in to ensure that we can prevent binding symbols tha    t don't meet the action restrictions

    for a in actions:
        r = {f: None for f in a.params}
        for bindings in ground(a.param_restrictions, symbols):
            for formal, val in zip(a.params, bindings):
                r[formal] = val

            ga = bind_action(a, r)
            yield ga
