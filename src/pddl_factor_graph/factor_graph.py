import numpy as np
from scipy.optimize import least_squares
from typing import Callable, Dict, List, Optional
from pddl_factor_graph.factor import Factor
from pddl_factor_graph.variable import Variable


class FactorGraph:
    def __init__(self):
        self.factors: List[Factor] = []
        self.variables: Dict[str, Variable] = {}

    def add_variable(self, name: str, dim: int) -> Variable:
        v = Variable(name, dim)
        self.variables[name] = v
        return v

    def ensure_variable(self, name: str, dim: int) -> Variable:
        if name in self.variables:
            v = self.variables[name]
            if v.dim != dim:
                raise Exception(
                    f"Requested variable {name} with dim {dim}, but {name} is already in factor graph with dim {v.dim}"
                )
            return v
        else:
            return self.add_variable(name, dim)

    def add_factor(
        self,
        residual_fn: Callable,
        variables: List[Variable],
        sqrt_info: Optional[np.ndarray] = None,
    ):
        self.factors.append(Factor(residual_fn, variables, sqrt_info))

    def solve(self, initial: Dict[str, np.ndarray], **scipy_kwargs) -> dict:
        # --- build a flat parameter vector layout ---
        var_order = sorted(self.variables.keys())
        slices: Dict[str, slice] = {}
        offset = 0
        for name in var_order:
            dim = self.variables[name].dim
            slices[name] = slice(offset, offset + dim)
            offset += dim
        total_dim = offset

        # --- pack initial values ---
        x0 = np.zeros(total_dim)
        for name in var_order:
            x0[slices[name]] = np.asarray(initial[name]).ravel()

        # --- stacked residual function ---
        def residual_vector(x):
            blocks = []
            for f in self.factors:
                vals = [x[slices[v.name]] for v in f.variables]
                r = np.atleast_1d(f.residual_fn(*vals))
                if f.sqrt_info is not None:
                    r = f.sqrt_info @ r
                blocks.append(r)
            return np.concatenate(blocks)

        # --- solve ---
        defaults = dict(method="trf", verbose=0)
        defaults.update(scipy_kwargs)
        result = least_squares(residual_vector, x0, **defaults)

        # --- unpack ---
        solution = {name: result.x[slices[name]] for name in var_order}
        return solution, result
