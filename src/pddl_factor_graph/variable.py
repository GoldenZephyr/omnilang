from dataclasses import dataclass


@dataclass
class Variable:
    name: str
    dim: int
