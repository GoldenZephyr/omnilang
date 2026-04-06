import numpy as np
import spark_dsg

from omnilang.testing_scene_graphs.utils import initialize_new_dsg, id_from_label


def add_object_to_place(
    G: spark_dsg.SceneGraph,
    object_label,
    object_idx,
    place: spark_dsg.NodeSymbol,
    offset=np.array([0.1, 0.1, 0]),
):
    obj = spark_dsg.ObjectNodeAttributes()

    place_node = G.find_node(place.value)
    if place_node is None:
        raise Exception(f"Couldn't find {place} in scene graph!")

    obj.position = place_node.attributes.position + offset
    obj.semantic_label = id_from_label(object_label)
    object_ns = spark_dsg.NodeSymbol("o", object_idx)
    G.add_node(spark_dsg.DsgLayers.OBJECTS, object_ns.value, obj)
    G.insert_edge(place, object_ns)


def build_NxN_dsg(rows, cols):
    G = initialize_new_dsg()

    unit = 1.0
    idx = 0
    rc_to_ns = {}
    for r in range(rows):
        y = r * unit
        for c in range(cols):
            x = c * unit
            place = spark_dsg.TraversabilityNodeAttributes()
            place.position = np.array([x, y, 0])
            new_ns = spark_dsg.NodeSymbol("t", idx)
            G.add_node(
                spark_dsg.DsgLayers.TRAVERSABILITY,
                new_ns.value,
                place,
            )
            rc_to_ns[(r, c)] = new_ns
            idx += 1

            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if abs(dr) == abs(dc):
                        continue
                    rr = r + dr
                    cc = c + dc
                    # if 0 <= rr < rows and 0 <= cc < cols:
                    if (rr, cc) in rc_to_ns:
                        neighbor = rc_to_ns[(rr, cc)]
                        G.insert_edge(new_ns, neighbor)

    return G


def add_grid_regions(G: spark_dsg.SceneGraph, offset: float, region_size: float):
    regions = {}
    for n in G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY).nodes:
        x, y = n.attributes.position[:2]
        c = (x - offset) // region_size
        r = (y - offset) // region_size
        assert (
            r >= 0
        ), "Currently assumes all places for adding regions are in 'positive' quadrant"
        assert (
            c >= 0
        ), "Currently assumes all places for adding regions are in 'positive' quadrant"
        if (r, c) not in regions:
            regions[(r, c)] = []
        regions[(r, c)].append(n)
    max_col = max([c for r, c in regions.keys()])
    for (r, c), children_places in regions.items():
        region = spark_dsg.RoomNodeAttributes()
        region.position = np.array(
            [c * region_size - 2 * offset, r * region_size - 2 * offset, 0]
        )
        idx = int(r * (max_col + 1) + c)
        new_ns = spark_dsg.NodeSymbol("r", idx)

        G.add_node(
            spark_dsg.DsgLayers.ROOMS,
            new_ns.value,
            region,
        )
        for place in children_places:
            G.insert_edge(new_ns, place.id.value)

    for r1, c1 in regions.keys():
        idx1 = int(r1 * (max_col + 1) + c1)
        ns1 = spark_dsg.NodeSymbol("r", idx1)
        for r2, c2 in regions.keys():
            dr = r2 - r1
            dc = c2 - c1
            if abs(dr) + abs(dc) == 1:
                idx2 = int(r2 * (max_col + 1) + c2)
                ns2 = spark_dsg.NodeSymbol("r", idx2)
                G.insert_edge(ns1, ns2)


if __name__ == "__main__":
    from dsg_exploration_sim.plotting import plot_layer, plot_interlayer_edges
    import matplotlib.pyplot as plt

    G = build_NxN_dsg(3, 3)

    add_object_to_place(G, "box", 1, spark_dsg.NodeSymbol("t", 3))

    plot_layer(G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY), alpha=0.4)
    plot_layer(G.get_layer(spark_dsg.DsgLayers.OBJECTS), node_color="c", alpha=0.4)
    plot_interlayer_edges(
        G,
        spark_dsg.DsgLayers.TRAVERSABILITY,
        spark_dsg.DsgLayers.OBJECTS,
        edge_color="k",
        alpha=0.4,
    )
    # plot_frontiers(G)
    plt.show()
