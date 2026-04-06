from omnilang.testing_scene_graphs import (
    add_object_to_place,  # noqa
    plot_dsg,
)
from region_grid_world import setup_dsg
import matplotlib.pyplot as plt

# G = build_NxN_dsg(9, 9)
# add_grid_regions(G, -0.5, 3)
G, Gobs, sim_state = setup_dsg()
plot_dsg(G, 0.2)
plot_dsg(Gobs, 1)

plt.show()
