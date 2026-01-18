from omnilang.graph_builder import build_expanded_test_dsg
from omnilang.mdp_states import DsgEnvironment, Environment, Fact, Symbol
import numpy as np

G = build_expanded_test_dsg()

dsg_env = DsgEnvironment(G)

Fact
env = Environment(
    dsg_env, {Symbol("t1"), Symbol("a1")}, {Symbol("t1"): "place", Symbol("a1"): "idk"}
)
env.attach_metadata(Symbol("u1"), {"position": np.array([1, 2, 3])})
env.attach_metadata("a1", {"humor": "good"})

print("O1: ", env.get_metadata_for_symbol("O1"))
print("u1: ", env.get_metadata_for_symbol("u1"))

print("Symbols with position: ", env.get_symbols_with_metadata("position"))
