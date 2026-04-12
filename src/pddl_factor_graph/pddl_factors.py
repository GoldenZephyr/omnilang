from dataclasses import dataclass
import numpy as np
from typing import Callable
import inspect


@dataclass
class UninitializedValue:
    dim: int
    initial_guess: np.ndarray = None


@dataclass
class PddlFactor:
    function: Callable
    residual_dimension: int
    precision: float

    def get_formal_param_names(self):
        sig = inspect.signature(self.function)
        formal_param_names = sig.parameters.keys()
        return formal_param_names


def near_factor(s: dict, t: dict, expected_distance=1):
    return expected_distance - np.linalg.norm(s["position"] - t["position"])
