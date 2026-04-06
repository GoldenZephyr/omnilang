from dataclasses import dataclass
from typing import Callable, List, Optional
from pddl_factor_graph.variable import Variable
import numpy as np


@dataclass
class Factor:
    residual_fn: Callable  # (*variable_values) -> 1D np.array
    variables: List[Variable]
    sqrt_info: Optional[np.ndarray] = None  # weights the residual: r' = sqrt_info @ r
