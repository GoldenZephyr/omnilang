import omnilang as oml
from pddl_factor_graph.factor_graph import FactorGraph
from typing import Callable
import numpy as np
from pddl_factor_graph.pddl_factors import UninitializedValue, PddlFactor


def pddl_state_to_factor_graph(
    env: oml.Environment, state: oml.State, predicate_to_factor: dict[str, PddlFactor]
) -> FactorGraph:
    graph = FactorGraph()

    def is_generated(s: oml.Symbol):
        return "generator" in env.get_metadata_for_symbol(s)

    def constrains_generated_variable(f: oml.Fact):
        return any(is_generated(s) for s in f.body)

    def make_guess(dim: int):
        return np.random.normal(size=dim)

    initial_guess = {}
    for fact in state.facts:
        if constrains_generated_variable(fact):
            print(f"Adding pddl factor for {fact}")
            if fact.head not in predicate_to_factor:
                continue
            pddl_factor = predicate_to_factor[fact.head]
            print("pddl_factor:", pddl_factor)

            bound_metadata = {}  # formal factor param name -> {metadata_key: metadata_value}
            argidx_to_param_and_key = []  # arg idx -> [(formal_param_name, metadata_key)]
            lifted_vars = []
            lifted_formal_params = []
            for var, formal_param_name in zip(
                fact.body, pddl_factor.get_formal_param_names()
            ):
                metadata = env.get_metadata_for_symbol(var)
                if is_generated(var):
                    bound_metadata[formal_param_name] = {}
                    for metadatum, value in metadata.items():
                        if isinstance(value, UninitializedValue):
                            var_name = f"{var.identifier}-{metadatum}"
                            var_dim = value.dim
                            if var_name not in initial_guess:
                                guess = value.initial_guess
                                if guess is None:
                                    guess = make_guess(var_dim)
                                initial_guess[var_name] = guess
                            fg_var = graph.ensure_variable(var_name, var_dim)
                            lifted_vars.append(fg_var)
                            lifted_formal_params.append(formal_param_name)
                            argidx_to_param_and_key.append(
                                (formal_param_name, metadatum)
                            )
                        else:
                            bound_metadata[formal_param_name][metadatum] = value
                else:
                    bound_metadata[formal_param_name] = metadata

            def grounded_residual_function(
                *lifted_args,
                fact=fact,
                bound_metadata=bound_metadata,
                argidx_to_param_and_key=argidx_to_param_and_key,
                pddl_factor=pddl_factor,
            ):
                grounded_metadata = {k: {} for k in bound_metadata.keys()}
                for val, (formal_param_name, metadata_key) in zip(
                    lifted_args, argidx_to_param_and_key
                ):
                    grounded_metadata[formal_param_name][metadata_key] = val

                joint_metadata = {
                    k: grounded_metadata[k] | bound_metadata[k]
                    for k in grounded_metadata.keys()
                }

                residual = pddl_factor.function(**joint_metadata)
                return residual

            graph.add_factor(
                residual_fn=grounded_residual_function,
                variables=lifted_vars,
                sqrt_info=pddl_factor.precision
                * np.eye(pddl_factor.residual_dimension),
            )
    return graph, initial_guess


def resolve_uninitialized_variables(
    env: oml.Environment,
    pddl_state: oml.State,
    predicate_to_factor: dict[str, Callable],
):
    fg, initial_guess = pddl_state_to_factor_graph(env, pddl_state, predicate_to_factor)

    solution, result = fg.solve(initial_guess)
    for var_name, value in solution.items():
        symbol, metadatum = var_name.split("-")
        print(f"Attaching metadata {metadatum} for {symbol}")
        print("Metadata before: ", env.get_metadata_for_symbol(oml.Symbol(symbol)))
        env.attach_metadata(oml.Symbol(symbol), {metadatum: value})
        print("Metadata after: ", env.get_metadata_for_symbol(oml.Symbol(symbol)))
    return solution, result
