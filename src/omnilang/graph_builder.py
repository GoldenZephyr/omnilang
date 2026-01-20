import numpy as np
import spark_dsg


def build_test_dsg():
    G = spark_dsg.DynamicSceneGraph()
    G.add_layer(2, 0, spark_dsg.DsgLayers.OBJECTS)
    G.add_layer(3, 0, spark_dsg.DsgLayers.PLACES)
    G.add_layer(3, 1, spark_dsg.DsgLayers.TRAVERSABILITY)
    G.add_layer(4, 0, spark_dsg.DsgLayers.ROOMS)
    G.add_layer(5, 0, spark_dsg.DsgLayers.BUILDINGS)

    room = spark_dsg.RoomNodeAttributes()
    room.position = np.array([0, 0, 0])
    room.semantic_label = 0

    G.add_node(spark_dsg.DsgLayers.ROOMS, spark_dsg.NodeSymbol("R", 0).value, room)

    place1 = spark_dsg.PlaceNodeAttributes()
    place1.position = np.array([-1, 0, 0])
    G.add_node(spark_dsg.DsgLayers.PLACES, spark_dsg.NodeSymbol("p", 0).value, place1)
    place2 = spark_dsg.PlaceNodeAttributes()
    place2.position = np.array([1, 0, 0])
    G.add_node(spark_dsg.DsgLayers.PLACES, spark_dsg.NodeSymbol("p", 1).value, place2)

    place1_trav = spark_dsg.TraversabilityNodeAttributes()
    place1_trav.position = np.array([-1.1, 0, 0])
    G.add_node(
        spark_dsg.DsgLayers.TRAVERSABILITY,
        spark_dsg.NodeSymbol("t", 0).value,
        place1_trav,
    )
    place2_trav = spark_dsg.TraversabilityNodeAttributes()
    place2_trav.position = np.array([1.1, 0, 0])
    G.add_node(
        spark_dsg.DsgLayers.TRAVERSABILITY,
        spark_dsg.NodeSymbol("t", 1).value,
        place2_trav,
    )

    frontier1 = spark_dsg.PlaceNodeAttributes()
    frontier1.position = np.array([1.5, 0.2, 0])
    frontier1.real_place = False
    G.add_node(
        spark_dsg.DsgLayers.PLACES, spark_dsg.NodeSymbol("f", 0).value, frontier1
    )

    obj1 = spark_dsg.ObjectNodeAttributes()
    obj1.position = np.array([-1.5, 0, 0])
    obj1.semantic_label = 34  # box
    G.add_node(spark_dsg.DsgLayers.OBJECTS, spark_dsg.NodeSymbol("O", 0).value, obj1)

    obj2 = spark_dsg.ObjectNodeAttributes()
    obj2.position = np.array([1.5, 0.1, 0])
    obj2.semantic_label = 15  # rock
    G.add_node(spark_dsg.DsgLayers.OBJECTS, spark_dsg.NodeSymbol("O", 1).value, obj2)

    G.insert_edge(
        spark_dsg.NodeSymbol("R", 0).value, spark_dsg.NodeSymbol("p", 0).value
    )
    G.insert_edge(
        spark_dsg.NodeSymbol("R", 0).value, spark_dsg.NodeSymbol("p", 1).value
    )
    G.insert_edge(
        spark_dsg.NodeSymbol("p", 0).value, spark_dsg.NodeSymbol("p", 1).value
    )
    G.insert_edge(
        spark_dsg.NodeSymbol("t", 0).value, spark_dsg.NodeSymbol("O", 0).value
    )
    G.insert_edge(
        spark_dsg.NodeSymbol("t", 1).value, spark_dsg.NodeSymbol("O", 1).value
    )
    G.insert_edge(
        spark_dsg.NodeSymbol("t", 0).value, spark_dsg.NodeSymbol("t", 1).value
    )

    G.insert_edge(
        spark_dsg.NodeSymbol("f", 0).value, spark_dsg.NodeSymbol("t", 1).value
    )

    labelspaces = {
        "labelspaces": {
            "_l2p0": [
                [0, "unknown"],
                [1, "sky"],
                [2, "tree"],
                [3, "water"],
                [4, "ground"],
                [5, "grass"],
                [6, "sand"],
                [7, "sidewalk"],
                [8, "dock"],
                [9, "road"],
                [10, "path"],
                [11, "vehicle"],
                [12, "building"],
                [13, "shelter"],
                [14, "signal"],
                [15, "rock"],
                [16, "fence"],
                [17, "boat"],
                [18, "sign"],
                [19, "hill"],
                [20, "bridge"],
                [21, "wall"],
                [22, "floor"],
                [23, "ceiling"],
                [24, "door"],
                [25, "stairs"],
                [26, "pole"],
                [27, "rail"],
                [28, "structure"],
                [29, "window"],
                [30, "surface"],
                [31, "flora"],
                [32, "flower"],
                [33, "bed"],
                [34, "box"],
                [35, "storage"],
                [36, "barrel"],
                [37, "bag"],
                [38, "basket"],
                [39, "seating"],
                [40, "flag"],
                [41, "decor"],
                [42, "light"],
                [43, "appliance"],
                [44, "trash"],
                [45, "bicycle"],
                [46, "food"],
                [47, "clothes"],
                [48, "thing"],
                [49, "animal"],
                [50, "human"],
            ],
            "_l4p0": [
                [0, "unknown"],
                [1, "road"],
                [2, "field"],
                [3, "shelter"],
                [4, "indoor"],
                [5, "stairs"],
                [6, "sidewalk"],
                [7, "path"],
                [8, "boundary"],
                [9, "shore"],
                [10, "ground"],
                [11, "dock"],
                [12, "parking"],
                [13, "footing"],
            ],
        }
    }

    G.metadata.add(labelspaces)

    return G


def build_expanded_test_dsg():
    G = build_test_dsg()

    for idx in range(10):
        place = spark_dsg.TraversabilityNodeAttributes()
        place.position = np.array([2 + idx, 0, 0])
        G.add_node(
            spark_dsg.DsgLayers.TRAVERSABILITY,
            spark_dsg.NodeSymbol("t", 2 + idx).value,
            place,
        )
        G.insert_edge(
            spark_dsg.NodeSymbol("t", 2 + idx).value, spark_dsg.NodeSymbol("t", 1 + idx)
        )

    food = spark_dsg.ObjectNodeAttributes()
    food.position = np.array([7, 0.1, 0])
    food.semantic_label = 46  # food
    G.add_node(spark_dsg.DsgLayers.OBJECTS, spark_dsg.NodeSymbol("O", 99).value, food)

    G.insert_edge(
        spark_dsg.NodeSymbol("O", 99).value, spark_dsg.NodeSymbol("t", 7).value
    )

    return G


if __name__ == "__main__":
    from dsg_exploration_sim.plotting import plot_layer, plot_frontiers
    import matplotlib.pyplot as plt

    G = build_test_dsg()

    plot_layer(G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY))
    plot_layer(G.get_layer(spark_dsg.DsgLayers.OBJECTS), node_color="c")
    plot_frontiers(G)
    plt.show()
