import omnilang as oml
from clingo_stream_planning.clingo_utils import (
    variable_to_clingo,
    to_clingo_type_string,
)
from dataclasses import dataclass


@dataclass
class DpGenerationContext:
    intermediate_prefix: str
    trigger_type: str
    param_to_type: dict[oml.Symbol, str]
    counter: list[int]


def generate_derived_predicate_clingo(domain: oml.FullDomain):
    derived_predicates = domain.pddl_domain.derived_predicates
    if derived_predicates is None:
        return []

    lines = []
    for dp in derived_predicates:
        aux_dp, original_dp = derived_predicate_to_clingo(dp)

        # print("aux dp clingo: ")
        # for l in aux_dp:  # E: Ambiguous variable name: `l`
        #    print(l)
        # print("og dp clingo: ")
        # for l in original_dp:  # E: Ambiguous variable name: `l`
        #    print(l)
        lines += aux_dp + original_dp

    return lines


def build_derived_predicate_and_constraints(
    name: str,
    params: list[oml.Symbol],
    types: list[str],
    quantified_params: list[oml.Symbol],
    quantified_types: list[str],
):
    full_params = params + quantified_params
    full_types = types + quantified_types

    constraints = []
    for p, t in zip(full_params, full_types):
        var = variable_to_clingo(p)
        constraints.append(to_clingo_type_string(var, t))
        constraints.append(f"inworld({var})")
    pred_constraints = ", ".join(constraints)

    print("full params: ", full_params)
    if len(full_params) > 0:
        parm_str = ", " + ", ".join(map(variable_to_clingo, full_params))
    else:
        parm_str = ""

    derived_pred = f'derivedPredicate(("{name}"{parm_str}))'
    return derived_pred, pred_constraints


def build_derived_variable_and_constraints(name, params, types):
    parms = ", ".join(map(variable_to_clingo, params))

    constraints = []
    for p, t in zip(params, types):
        var = variable_to_clingo(p)
        constraints.append(to_clingo_type_string(var, t))
        constraints.append(f"inworld({var})")
    input_constraints = ", ".join(constraints)

    if len(parms) > 0:
        parm_str = " , " + parms
    else:
        parm_str = ""
    derived_var = f'variable(("{name}"{parm_str}))'
    return derived_var, input_constraints


def derived_predicate_to_clingo(dp: oml.DerivedPredicate, counter=[0], prefix=None):
    # (forall (?p - place) (implies (possibly-object ?o ?p) (observed ?p)))
    # derivedPredicate({derived_predicate}) :-

    match dp.body:
        case oml.Disjunction():
            trigger_type = "or"
        case _:
            trigger_type = "and"

    derived_var, var_input_constraints = build_derived_variable_and_constraints(
        dp.name, dp.params, dp.types
    )

    if len(var_input_constraints) > 0:
        lines = [f"derivedVariable({derived_var}) :- {var_input_constraints}."]
    else:
        lines = [f"derivedVariable({derived_var})."]

    param_to_type = {p: t for p, t in zip(dp.params, dp.types)}
    print("param to type: ", param_to_type)
    if prefix is None:
        prefix = dp.name
    new_dp_lines, new_lines, quantified_children = dp_formula_to_clingo(
        param_to_type, prefix, trigger_type, dp.body, counter
    )

    derived_pred, pred_input_constriants = build_derived_predicate_and_constraints(
        dp.name,
        dp.params,
        dp.types,
        list(quantified_children.keys()),
        list(quantified_children.values()),
    )

    lines.append(
        f"derivedPredicate({derived_pred}, type({trigger_type})) :- {pred_input_constriants}."
    )

    # Fill in the derived predicate for each of the lines, which we can't know
    # until after they have all been generated
    new_lines = [nl(derived_pred) if callable(nl) else nl for nl in new_lines]

    lines += new_lines
    lines.append(
        f"postcondition({derived_pred}, type({trigger_type}), effect(unconditional), {derived_var}, value({derived_var}, true)) :- derivedPredicate({derived_pred}, type({trigger_type}))."
    )

    return new_dp_lines, lines


def make_dp_precondition(
    trigger_type: str,
    var: str,
    val: str,
):
    def make_str(dp_string: str):
        return f"precondition({dp_string}, type({trigger_type}), {var}, value({var}, {val})) :- derivedPredicate({dp_string}, type({trigger_type}))."

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
    parms = ", ".join(variable_to_clingo(p) for p in formula.body)
    var = f'variable(("{formula.head}", {parms}))'
    new_og_lines = make_dp_precondition(trigger_type, var, val)

    return [], new_og_lines, {}


def generate_merged_junction(
    formula: oml.Conjunction | oml.Disjunction,
    intermediate_prefix,
    trigger_type,
    param_to_type,
    counter,
):
    """We are merging a conjunction inside a conjunction or a disjunction inside a disjunction"""
    new_intermediate_lines = []
    new_og_lines = []
    print("conjunction clauses: ", formula.clauses)
    quantified_children = {}
    for c in formula.clauses:
        if isinstance(c, oml.Bool):
            continue
        new_int, new_og, qc = dp_formula_to_clingo(
            param_to_type,
            intermediate_prefix,
            trigger_type,
            c,
            counter,
        )
        new_intermediate_lines += new_int
        new_og_lines += new_og
        quantified_children |= qc

    print("returning new_intermediate lines: ", new_intermediate_lines)
    return new_intermediate_lines, new_og_lines, quantified_children


def generate_subordinate_junction(
    formula: oml.Conjunction | oml.Disjunction,
    intermediate_prefix,
    trigger_type,
    param_to_type,
    counter,
):
    """We are adding a new derived predicate for a conjunction inside a disjunction or vice versa"""
    params = formula.get_params_matching(
        lambda x: isinstance(x, oml.Symbol)
        and (x.identifier.startswith("?") or x.identifier.startswith("&"))
    )
    params = list(set(params))
    types = [param_to_type[p] for p in params]
    idx = counter[0]
    counter[0] += 1
    derived_var = f"intermediate{idx}"
    new_dp = oml.DerivedPredicate(derived_var, params, types, formula, counter)

    parm_str = ", ".join(variable_to_clingo(p) for p in params)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    int_int, og_int = derived_predicate_to_clingo(new_dp, counter, intermediate_prefix)
    new_intermediate_lines = int_int + og_int
    new_og_lines = make_dp_precondition(trigger_type, derived_var_str, "true")
    print("2returning new_intermediate lines: ", new_intermediate_lines)
    return new_intermediate_lines, new_og_lines, {}


def generate_dp_body_junction(
    formula: oml.Conjunction | oml.Disjunction,
    intermediate_prefix: str,
    trigger_type: str,
    param_to_type: dict[oml.Symbol, str],
    counter: list[int],
):
    if (isinstance(formula, oml.Conjunction) and trigger_type == "and") or (
        isinstance(formula, oml.Disjunction) and trigger_type == "or"
    ):
        return generate_merged_junction(
            formula,
            intermediate_prefix,
            trigger_type,
            param_to_type,
            counter,
        )
    else:
        return generate_subordinate_junction(
            formula,
            intermediate_prefix,
            trigger_type,
            param_to_type,
            counter,
        )


def generate_dp_body_universal(
    formula: oml.UniversalQuantifier,
    intermediate_prefix: str,
    trigger_type: str,
    param_to_type: dict[oml.Symbol, str],
    counter: list[int],
):
    domain = formula.domain

    if isinstance(formula.body, oml.Implication):
        print("implication body: ", formula)
        # domain += formula.body.head
        domain = oml.Conjunction([domain, formula.body.head])
        body = oml.Negation(formula.body.body)
    else:
        body = oml.Negation(formula.body)

    idx = counter[0]
    counter[0] += 1
    derived_var = f"intermediate{idx}"
    inverted_formula = oml.ExistentialQuantifier(
        formula.formal_params, formula.param_types, body, domain
    )
    parm_str = ", ".join(variable_to_clingo(p) for p in param_to_type)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    new_dp = oml.DerivedPredicate(
        derived_var,
        list(param_to_type.keys()),
        list(param_to_type.values()),
        inverted_formula,
    )

    int_int, og_int = derived_predicate_to_clingo(new_dp, counter, intermediate_prefix)
    new_intermediate_lines = int_int + og_int

    new_og_lines = make_dp_precondition(trigger_type, derived_var_str, "false")
    print("3returning new_intermediate lines: ", new_intermediate_lines)
    return new_intermediate_lines, new_og_lines, {}


def generate_dp_body_existential(
    formula: oml.ExistentialQuantifier,
    intermediate_prefix: str,
    trigger_type: str,
    param_to_type: dict[oml.Symbol, str],
    counter: list[int],
):
    params = formula.get_params_matching(
        lambda x: isinstance(x, oml.Symbol)
        and (x.identifier.startswith("?") or x.identifier.startswith("&"))
    )
    params = list(set(params))
    for p, t in zip(formula.formal_params, formula.param_types):
        param_to_type[p] = t
    # NOTE: this param logic probably isn't quite right for more deeply nested clauses
    # Specifically, we want to skip lifted params that are introduced by descendant quantified expressions.

    types = [param_to_type[p] for p in params]

    idx = counter[0]
    counter[0] += 1
    derived_var = f"intermediate{idx}"
    parm_str = ", ".join(variable_to_clingo(p) for p in params)
    derived_var_str = f'variable(("{derived_var}", {parm_str}))'

    new_formula = oml.Conjunction([formula.domain, formula.body])
    new_dp = oml.DerivedPredicate(derived_var, params, types, new_formula)

    int_int, og_int = derived_predicate_to_clingo(new_dp, counter, intermediate_prefix)
    new_intermediate_lines = int_int + og_int

    new_og_lines = make_dp_precondition(
        trigger_type,
        derived_var_str,
        "true",
    )

    quantified_vars = {p: t for p, t in zip(formula.formal_params, formula.param_types)}
    print("4returning new_intermediate lines: ", new_intermediate_lines)
    return new_intermediate_lines, new_og_lines, quantified_vars


def generate_dp_body_negation(
    formula: oml.ExistentialQuantifier,
    intermediate_prefix: str,
    trigger_type: str,
    param_to_type: dict[oml.Symbol, str],
    counter: list[int],
):
    match formula.clause:
        case oml.Fact() | oml.NegatedFact():
            # If the body is a fact, then generate precondition for negated fact.
            x, new_og_lines, y = dp_formula_to_clingo(
                param_to_type,
                intermediate_prefix,
                trigger_type,
                oml.negate(formula.clause),
                counter,
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
            types = [param_to_type[p] for p in params]

            idx = counter[0]
            counter[0] += 1
            derived_var = f"intermediate{idx}"
            parm_str = ", ".join(variable_to_clingo(p) for p in params)
            derived_var_str = f'variable(("{derived_var}", {parm_str}))'

            new_dp = oml.DerivedPredicate(derived_var, params, types, formula.clause)

            int_int, og_int = derived_predicate_to_clingo(
                new_dp, counter, intermediate_prefix
            )
            new_intermediate_lines = int_int + og_int

            new_og_lines = make_dp_precondition(trigger_type, derived_var_str, "false")

            return new_intermediate_lines, new_og_lines


def dp_formula_to_clingo(
    param_to_type: dict[oml.Symbol, str],
    intermediate_prefix: str,
    trigger_type: str,
    formula,
    counter: list[int],
):
    print(formula)
    print(type(formula))
    match formula:
        case oml.Fact() | oml.NegatedFact():
            return generate_dp_body_atomic(formula, trigger_type)

        case oml.Conjunction() | oml.Disjunction():
            return generate_dp_body_junction(
                formula,
                intermediate_prefix,
                trigger_type,
                param_to_type,
                counter,
            )
        case oml.UniversalQuantifier():
            return generate_dp_body_universal(
                formula,
                intermediate_prefix,
                trigger_type,
                param_to_type,
                counter,
            )

        case oml.ExistentialQuantifier():
            return generate_dp_body_existential(
                formula,
                intermediate_prefix,
                trigger_type,
                param_to_type,
                counter,
            )

        case oml.Negation():
            return generate_dp_body_negation(
                formula,
                intermediate_prefix,
                trigger_type,
                param_to_type,
                counter,
            )

        case oml.Bool():
            return [], [], {}

        case _:
            raise Exception(
                f"Don't know how to handle {formula} in derived predicate condition"
            )
