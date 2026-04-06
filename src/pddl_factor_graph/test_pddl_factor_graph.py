from omnilang import Symbol, Fact
import omnilang as oml
import numpy as np
from pddl_factor_graph.pddl_factor_graph_solver import resolve_uninitialized_variables
from pddl_factor_graph.pddl_factors import UninitializedValue, PddlFactor


def near_factor(s: dict, t: dict):
    return np.linalg.norm(s["position"] - t["position"])


symbols = [Symbol("p1"), Symbol("p2"), Symbol("predicted1")]
symbol_to_type = {}
symbol_to_type[Symbol("p1")] = "place"
symbol_to_type[Symbol("p2")] = "place"
symbol_to_type[Symbol("predicted1")] = "place"
facts = {
    Fact("near", [Symbol("p1"), Symbol("predicted1")]),
    Fact("near", [Symbol("p2"), Symbol("predicted1")]),
}
env = oml.Environment(None, symbols, symbol_to_type, {"place": "object"})
env.attach_metadata(Symbol("p1"), {"position": np.array([0.0, 0.0])})
env.attach_metadata(Symbol("p2"), {"position": np.array([10.0, 0.0])})
env.attach_metadata(
    Symbol("predicted1"),
    {"generator": True, "position": UninitializedValue(2, np.array([0.01, 0.5]))},
)
pddl_state = oml.State(facts)
predicate_to_factor = {}
predicate_to_factor["near"] = PddlFactor(near_factor, 1.0)

solution, result = resolve_uninitialized_variables(
    env,
    pddl_state,
    predicate_to_factor,
)
