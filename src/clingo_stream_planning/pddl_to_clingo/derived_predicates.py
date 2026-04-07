import omnilang as oml
from clingo_stream_planning.pddl_to_clingo.compiler_utils import (
    variable_to_clingo,
    symbol_to_clingo,
    to_clingo_type_string,
)
from dataclasses import dataclass


@dataclass
class DpGenerationContext:
    intermediate_prefix: str
    trigger_type: str
    param_to_type: dict[oml.Symbol, str]
    counter: list[int]


def generate_derived_predicates(
    env: oml.Environment, domain: oml.FullDomain, state: oml.State
):
    """Entrypoint for generating clingo for all derived predicates"""
    derived_predicates = domain.pddl_domain.derived_predicates
    if derived_predicates is None:
        return []
    lines = ["% Derived Predicates"]
    for dp in derived_predicates:
        aux_dp, original_dp = derived_predicate_to_clingo(dp)
        lines += aux_dp
        lines[-1] += "\n"
        lines += original_dp + ["\n"]
    return lines


def derived_predicate_to_clingo(dp: oml.DerivedPredicate, counter=[0], prefix=None):
    """Turn a single derived predicate into clingo encoding"""

    match dp.body:
        case oml.Disjunction():
            trigger_type = "or"
        case _:
            trigger_type = "and"

    lines = declare_derived_variable(dp)

    param_to_type = {p: t for p, t in zip(dp.params, dp.types)}
    if prefix is None:
        prefix = dp.name

    cxt = DpGenerationContext(prefix, trigger_type, param_to_type, counter)
    new_dp_lines, precondition_lines, quantified_children = dp_formula_to_clingo(
        cxt, dp.body
    )
    lines += declare_derived_header(dp, quantified_children, trigger_type)
    lines += declare_preconditions(dp, precondition_lines, quantified_children)
    lines += declare_postconditions(dp, trigger_type, quantified_children)

    return new_dp_lines, lines


def declare_derived_variable(dp: oml.DerivedPredicate):
    derived_var, var_input_constraints = build_derived_variable_and_constraints(
        dp.name, dp.params, dp.types
    )

    lines = [""]
    lines += [f"% {str(oml.simplify(dp.body))}"]
    if len(var_input_constraints) > 0:
        lines += [f"derivedVariable({derived_var}) :- {var_input_constraints}."]
    else:
        lines += [f"derivedVariable({derived_var})."]
    return lines


def declare_derived_header(dp: oml.DerivedPredicate, quantified_children, trigger_type):
    derived_pred, pred_input_constriants = build_derived_predicate_and_constraints(
        dp.name,
        dp.params,
        dp.types,
        list(quantified_children.keys()),
        list(quantified_children.values()),
    )

    header = f"derivedPredicate({derived_pred}, type({trigger_type}))"
    if len(pred_input_constriants) > 0:
        return [f"{header} :- {pred_input_constriants}."]
    else:
        return [f"{header}."]


def declare_preconditions(dp, precondition_lines, quantified_children):
    # Fill in the derived predicate for each of the lines, which we can't know
    # until after they have all been generated
    derived_pred, pred_input_constriants = build_derived_predicate_and_constraints(
        dp.name,
        dp.params,
        dp.types,
        list(quantified_children.keys()),
        list(quantified_children.values()),
    )

    new_lines = [nl(derived_pred) if callable(nl) else nl for nl in precondition_lines]
    return new_lines


def declare_postconditions(dp, trigger_type, quantified_children):
    derived_pred, pred_input_constriants = build_derived_predicate_and_constraints(
        dp.name,
        dp.params,
        dp.types,
        list(quantified_children.keys()),
        list(quantified_children.values()),
    )
    derived_var, var_input_constraints = build_derived_variable_and_constraints(
        dp.name, dp.params, dp.types
    )

    header = f"derivedPredicate({derived_pred}, type({trigger_type}))"
    postcondition_str = f"postcondition({derived_pred}, type({trigger_type}), effect(unconditional), {derived_var}, value({derived_var}, true))"
    return [f"{postcondition_str} :- {header}."]


def build_derived_predicate_and_constraints(
    name: str,
    params: list[oml.Symbol],
    types: list[str],
    quantified_params: list[oml.Symbol],
    quantified_types: list[str],
):
    """derivedPredicate(("name", X, Y, Z)),   has(X, type("type")), inworld(X)"""
    full_params = params + quantified_params
    full_types = types + quantified_types

    kernel, pred_constraints = get_kernel_and_constraints(name, full_params, full_types)

    derived_pred = f"derivedPredicate(({kernel}))"
    return derived_pred, pred_constraints


def build_derived_variable_and_constraints(name, params, types):
    """return variable(("name", X, Y, Z)),   has(X, type("type")), inworld(X)"""

    kernel, input_constraints = get_kernel_and_constraints(name, params, types)
    derived_var = f"variable(({kernel}))"
    return derived_var, input_constraints


def get_kernel_and_constraints(name, params, types):
    constraints = []
    for p, t in zip(params, types):
        var = variable_to_clingo(p)
        constraints.append(to_clingo_type_string(var, t))
        constraints.append(f"inworld({var})")
    input_constraints = ", ".join(constraints)
    kernel = ", ".join((f'"{name}"',) + tuple(map(variable_to_clingo, params)))
    return kernel, input_constraints


def make_dp_precondition(
    trigger_type: str,
    var: str,
    val: str,
):
    def make_str(dp_string: str):
        header = f"derivedPredicate({dp_string}, type({trigger_type}))"
        precondition = f"precondition({dp_string}, type({trigger_type}), {var}, value({var}, {val}))"
        return f"{precondition} :- {header}."

    return [make_str]


def generate_dp_body_atomic(formula: oml.Fact | oml.NegatedFact, trigger_type: str):
    if isinstance(formula, oml.Fact):
        val = "true"
    elif isinstance(formula, oml.NegatedFact):
        val = "false"
    else:
        raise TypeError(
            f"generate_dp_body_atomic should be called with Fact or Negated fact, not {formula}"
        )
    kernel = ", ".join(
        (f'"{formula.head}"',) + tuple(symbol_to_clingo(p) for p in formula.body)
    )
    var = f"variable(({kernel}))"
    new_og_lines = make_dp_precondition(trigger_type, var, val)

    return [], new_og_lines, {}


def generate_merged_junction(
    generation_context: DpGenerationContext,
    formula: oml.Conjunction | oml.Disjunction,
):
    """We are merging a conjunction inside a conjunction or a disjunction inside a disjunction"""
    new_intermediate_lines = []
    new_og_lines = []
    quantified_children = {}
    for c in formula.clauses:
        if isinstance(c, oml.Bool):
            continue
        new_int, new_og, qc = dp_formula_to_clingo(
            generation_context,
            c,
        )
        new_intermediate_lines += new_int
        new_og_lines += new_og
        quantified_children |= qc

    return new_intermediate_lines, new_og_lines, quantified_children


def generate_subordinate_junction(
    generation_context: DpGenerationContext,
    formula: oml.Conjunction | oml.Disjunction,
):
    """We are adding a new derived predicate for a conjunction inside a disjunction or vice versa"""
    params = formula.get_params_matching(
        lambda x: isinstance(x, oml.Symbol)
        and (x.identifier.startswith("?") or x.identifier.startswith("&"))
    )
    params = list(set(params))
    types = [generation_context.param_to_type[p] for p in params]
    idx = generation_context.counter[0]
    generation_context.counter[0] += 1
    derived_var = f"intermediate{idx}"
    new_dp = oml.DerivedPredicate(
        derived_var, params, types, formula, generation_context.counter
    )

    parm_str = ", ".join(variable_to_clingo(p) for p in params)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    int_int, og_int = derived_predicate_to_clingo(
        new_dp, generation_context.counter, generation_context.intermediate_prefix
    )
    new_intermediate_lines = int_int + og_int
    new_og_lines = make_dp_precondition(
        generation_context.trigger_type, derived_var_str, "true"
    )
    return new_intermediate_lines, new_og_lines, {}


def generate_dp_body_junction(
    generation_context: DpGenerationContext,
    formula: oml.Conjunction | oml.Disjunction,
):
    if (
        isinstance(formula, oml.Conjunction)
        and generation_context.trigger_type == "and"
    ) or (
        isinstance(formula, oml.Disjunction) and generation_context.trigger_type == "or"
    ):
        return generate_merged_junction(
            generation_context,
            formula,
        )
    else:
        return generate_subordinate_junction(
            generation_context,
            formula,
        )


def generate_dp_body_universal(
    generation_context: DpGenerationContext,
    formula: oml.UniversalQuantifier,
):
    domain = formula.domain

    if isinstance(formula.body, oml.Implication):
        domain = oml.Conjunction([domain, formula.body.head])
        body = oml.Negation(formula.body.body)
    else:
        body = oml.Negation(formula.body)

    counter = generation_context.counter
    idx = counter[0]
    counter[0] += 1
    derived_var = f"intermediate{idx}"
    inverted_formula = oml.ExistentialQuantifier(
        formula.formal_params, formula.param_types, body, domain
    )

    param_to_type = generation_context.param_to_type
    parm_str = ", ".join(variable_to_clingo(p) for p in param_to_type)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    new_dp = oml.DerivedPredicate(
        derived_var,
        list(param_to_type.keys()),
        list(param_to_type.values()),
        inverted_formula,
    )

    int_int, og_int = derived_predicate_to_clingo(
        new_dp, counter, generation_context.intermediate_prefix
    )
    new_intermediate_lines = int_int + og_int

    new_og_lines = make_dp_precondition(
        generation_context.trigger_type, derived_var_str, "false"
    )
    return new_intermediate_lines, new_og_lines, {}


def generate_dp_body_existential(
    cxt: DpGenerationContext,
    formula: oml.ExistentialQuantifier,
):
    params = formula.get_params_matching(
        lambda x: isinstance(x, oml.Symbol)
        and (x.identifier.startswith("?") or x.identifier.startswith("&"))
    )
    params = list(set(params))
    for p, t in zip(formula.formal_params, formula.param_types):
        cxt.param_to_type[p] = t
    # NOTE: this param logic probably isn't quite right for more deeply nested clauses
    # Specifically, we want to skip lifted params that are introduced by descendant quantified expressions.

    types = [cxt.param_to_type[p] for p in params]

    idx = cxt.counter[0]
    cxt.counter[0] += 1
    derived_var = f"intermediate{idx}"
    parm_str = ", ".join(variable_to_clingo(p) for p in params)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    new_formula = oml.Conjunction([formula.domain, formula.body])
    new_dp = oml.DerivedPredicate(derived_var, params, types, new_formula)

    int_int, og_int = derived_predicate_to_clingo(
        new_dp, cxt.counter, cxt.intermediate_prefix
    )
    new_intermediate_lines = int_int + og_int

    new_og_lines = make_dp_precondition(
        cxt.trigger_type,
        derived_var_str,
        "true",
    )

    quantified_vars = {p: t for p, t in zip(formula.formal_params, formula.param_types)}
    return new_intermediate_lines, new_og_lines, quantified_vars


def generate_dp_body_negation(
    cxt: DpGenerationContext,
    formula: oml.ExistentialQuantifier,
):
    match formula.clause:
        case oml.Fact() | oml.NegatedFact():
            # If the body is a fact, then generate precondition for negated fact.
            x, new_og_lines, y = dp_formula_to_clingo(
                cxt,
                oml.negate(formula.clause),
            )
            assert (
                x == []
            )  # shouldn't be any new derived predicates because we know it's a Fact
            assert y == {}  # shouldn't be any new quantified variables
            return [], new_og_lines, {}
        case _:
            # Otherwise, negate the output of an intermediate stream.
            params = formula.get_params_matching(
                lambda x: isinstance(x, oml.Symbol)
                and (x.identifier.startswith("?") or x.identifier.startswith("&"))
            )
            params = list(set(params))
            types = [cxt.param_to_type[p] for p in params]

            idx = cxt.counter[0]
            cxt.counter[0] += 1
            derived_var = f"intermediate{idx}"
            kernel = ", ".join(
                (f'"{derived_var}"',) + tuple(variable_to_clingo(p) for p in params)
            )
            derived_var_str = f"variable(({kernel}))"

            new_dp = oml.DerivedPredicate(derived_var, params, types, formula.clause)

            int_int, og_int = derived_predicate_to_clingo(
                new_dp, cxt.counter, cxt.intermediate_prefix
            )
            new_intermediate_lines = int_int + og_int

            new_og_lines = make_dp_precondition(
                cxt.trigger_type, derived_var_str, "false"
            )

            return new_intermediate_lines, new_og_lines


def dp_formula_to_clingo(
    generation_context: DpGenerationContext,
    formula,
):
    formula = oml.simplify(formula)
    match formula:
        case oml.Fact() | oml.NegatedFact():
            return generate_dp_body_atomic(formula, generation_context.trigger_type)

        case oml.Conjunction() | oml.Disjunction():
            return generate_dp_body_junction(
                generation_context,
                formula,
            )
        case oml.UniversalQuantifier():
            return generate_dp_body_universal(
                generation_context,
                formula,
            )

        case oml.ExistentialQuantifier():
            return generate_dp_body_existential(
                generation_context,
                formula,
            )

        case oml.Negation():
            return generate_dp_body_negation(
                generation_context,
                formula,
            )

        case oml.Bool():
            return [], [], {}

        case _:
            raise Exception(
                f"Don't know how to handle {formula} in derived predicate condition"
            )
