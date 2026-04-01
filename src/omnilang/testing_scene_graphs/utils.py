import spark_dsg

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


def id_from_label(label: str):
    for idx, lbl in labelspaces["labelspaces"]["_l2p0"]:
        if lbl == label:
            return idx
    raise Exception(
        f"Label {label} not found in labelspace. Options are: {[lbl for _, lbl in labelspaces['labelspaces']['_l2p0']]}"
    )


def add_labelspaces(G):
    G.metadata.add(labelspaces)


def initialize_new_dsg():
    G = spark_dsg.DynamicSceneGraph()
    G.add_layer(2, 0, spark_dsg.DsgLayers.OBJECTS)
    G.add_layer(3, 0, spark_dsg.DsgLayers.PLACES)
    G.add_layer(3, 1, spark_dsg.DsgLayers.TRAVERSABILITY)
    G.add_layer(4, 0, spark_dsg.DsgLayers.ROOMS)
    G.add_layer(5, 0, spark_dsg.DsgLayers.BUILDINGS)

    add_labelspaces(G)
    return G
