from pddl_factor_graph.factor_graph import FactorGraph
import numpy as np

graph = FactorGraph()

p0 = graph.add_variable("p0", 2)  # (x, y)
p1 = graph.add_variable("p1", 2)
p2 = graph.add_variable("p2", 2)

# Prior on first pose: "we know we started near the origin"
graph.add_factor(
    residual_fn=lambda p: p - np.array([0.0, 0.0]),
    variables=[p0],
    sqrt_info=10.0 * np.eye(2),  # strong prior
)

# Odometry: p1 ≈ p0 + [1, 0]
graph.add_factor(
    residual_fn=lambda pa, pb: pb - pa - np.array([1.0, 0.0]),
    variables=[p0, p1],
    sqrt_info=5.0 * np.eye(2),
)

# Odometry: p2 ≈ p1 + [1, 0]
graph.add_factor(
    residual_fn=lambda pa, pb: pb - pa - np.array([1.0, 0.0]),
    variables=[p1, p2],
    sqrt_info=5.0 * np.eye(2),
)

# Landmark observation from p2: "landmark at (2.5, 1.0) seen at range 1.0"
landmark = np.array([2.5, 1.0])
graph.add_factor(
    residual_fn=lambda p: np.array([np.linalg.norm(p - landmark) - 1.0]),
    variables=[p2],
    sqrt_info=np.array([[3.0]]),
)

# ── Solve ─────────────────────────────────────────────────────────
initial = {
    "p0": np.array([0.1, 0.1]),
    "p1": np.array([1.1, 0.1]),
    "p2": np.array([2.1, 0.1]),
}

solution, raw = graph.solve(initial)

for name in sorted(solution):
    print(f"{name}: {solution[name]}")
print(f"\nFinal cost: {raw.cost:.6f}")
