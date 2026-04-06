import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    variable_to_clingo,
    to_clingo_type_string,
    get_static_predicates,
)


def generate_action_precondition(
    action_nugget: str, precondition: oml.Fact | oml.NegatedFact
):
    match precondition:
        case oml.Fact():
            val = "true"
        case oml.NegatedFact():
            val = "false"

    var_kernel, _ = parms_and_types_to_kernel_and_constraints(
        precondition.head, precondition.body, [None] * len(precondition.body), False
    )
    var_kernel_str = ", ".join(var_kernel)
    var_nugget = f"variable(({var_kernel_str}))"
    head = f"precondition({action_nugget}, {var_nugget}, value({var_nugget}, {val}))"

    return [f"{head} :- action({action_nugget})."]


def generate_action_preconditions(
    static_predicates: set, action_nugget: str, action: oml.LiftedAction
):
    def is_static(f: oml.Fact):
        return f.head in static_predicates

    lines = []
    for fact in action.precondition.positive_facts:
        if is_static(fact):
            continue
        lines += generate_action_precondition(
            action_nugget,
            fact,
        )
    for fact in action.precondition.negative_facts:
        if is_static(fact):
            continue
        lines += generate_action_precondition(
            action_nugget,
            oml.negate(fact),
        )

    return lines


def generate_action_postcondition(
    action_nugget: str, postcondition: oml.Fact | oml.NegatedFact
):
    match postcondition:
        case oml.Fact():
            val = "true"
        case oml.NegatedFact():
            val = "false"

    var_kernel, _ = parms_and_types_to_kernel_and_constraints(
        postcondition.head, postcondition.body, [None] * len(postcondition.body), False
    )
    var_kernel_str = ", ".join(var_kernel)
    var_nugget = f"variable(({var_kernel_str}))"
    head = f"postcondition({action_nugget}, effect(unconditional), {var_nugget}, value({var_nugget}, {val}))"

    return [f"{head} :- action({action_nugget})."]


def generate_action_postconditions(
    static_predicates: set, action_nugget: str, action: oml.LiftedAction
):
    def is_static(f: oml.Fact):
        return f.head in static_predicates

    lines = []
    for fact in action.positive_effect:
        if is_static(fact):
            raise Exception(f"Found static predicate in effect of {action}")
        lines += generate_action_postcondition(
            action_nugget,
            fact,
        )
    for fact in action.negative_effect:
        if is_static(fact):
            raise Exception(f"Found static predicate in effect of {action}")
        lines += generate_action_postcondition(
            action_nugget,
            oml.negate(fact),
        )

    return lines


def parms_and_types_to_kernel_and_constraints(
    name: str,
    params: list[oml.Symbol],
    param_types: list,
    include_inworld_constraints: bool = True,
):
    nugget = (name,)
    for p in params:
        nugget += variable_to_clingo(p)

    types = []
    if len(param_types) > 0 and isinstance(param_types[0], list):
        for parm, tp in zip(params, param_types):
            match tp:
                case []:
                    types.append("object")
                case [t]:
                    types.append(t)
                case _:
                    raise Exception(
                        f"Only support a single type restriction. {name} {parm} was given: {tp}"
                    )

    type_strings = []
    for p, t in zip(params, types):
        var = variable_to_clingo(p)
        type_strings.append(to_clingo_type_string(var, type))
        if include_inworld_constraints:
            type_strings.append("inworld({var})")

    return nugget, type_strings


# ("str", P1, P2) is the "kernel"
# action(("str", P1, P2)) is the nugget
# action(action(("str", P1, P2))) is the header


def generate_action(static_predicates: list, action: oml.LiftedAction):
    action_kernel, type_strings = parms_and_types_to_kernel_and_constraints(
        action.name, action.params, action.param_restrictions
    )
    kernel_str = ", ".join(action_kernel)
    nugget_str = f"action(({kernel_str}))"
    header_str = f"action({nugget_str})"

    # TODO: here is where we want to add more restrictions to pull static facts
    # out from the precondition and into the nugget constraint
    static_constraints = ", ".join(type_strings)
    lines = [f"{header_str} :- {static_constraints}."]

    lines += generate_action_preconditions(static_predicates, nugget_str, action)
    lines += generate_action_postconditions(static_predicates, nugget_str, action)
    return lines


def generate_normal_actions(
    env: oml.Environment,
    domain: oml.FullDomain,
    state: oml.State,
    enable_static_predicates=True,
):
    lines = ["% actions"]
    if enable_static_predicates:
        static_predicates = get_static_predicates(env, domain, state)
    else:
        static_predicates = set()
    for action in domain.pddl_domain.actions:
        lines += generate_action(static_predicates, action)
    return lines


def generate_group_actions(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    lines = ["% group actions"]
    for action in domain.pddl_domain.group_actions:
        lines += generate_group_action(action)
    return lines
