import spark_dsg
import numpy as np
from dsg_exploration_sim.plotting import (
    plot_layer,
    plot_interlayer_edges,
    plot_frontiers,
)
import omnilang as oml
import matplotlib.pyplot as plt
from dsg_exploration_sim.action_and_states import SimulationState


possible_layers = [
    spark_dsg.DsgLayers.OBJECTS,
    spark_dsg.DsgLayers.TRAVERSABILITY,
    spark_dsg.DsgLayers.ROOMS,
]


def layer_to_name(G: spark_dsg.SceneGraph, type_to_line: dict, new_prefix=""):
    new_dict = {}

    for type, line in type_to_line.items():
        remapped = False
        for pl in possible_layers:
            if type == G.get_layer_key(pl):
                new_dict[new_prefix + pl] = line
                remapped = True
                break
        if not remapped:
            new_dict[new_prefix + type] = line

    return new_dict


def plot_generated_env(env: oml.Environment, type_to_marker: dict):
    label_to_line = {}
    for type, marker in type_to_marker.items():
        to_plot = env.get_objects_of_type(type)
        positions = []
        for symbol in to_plot:
            m = env.get_metadata_for_symbol(symbol)
            if "generator" not in m:
                continue
            pos = m.get("position", None)
            if pos is not None:
                positions.append(pos[:2])
            else:
                print("Not position for: ", symbol)
        positions = np.array(positions)
        if len(positions) == 0:
            continue
        s = plt.scatter(*positions.T, marker=marker, s=400, alpha=0.8)
        label_to_line["predicted-" + type] = s
    return label_to_line


def plot_dsg(G: spark_dsg.DynamicSceneGraph, alpha=1):
    label_to_line = {}
    labels = plot_layer(
        G.get_layer(spark_dsg.DsgLayers.TRAVERSABILITY),
        alpha=alpha,
        text_offset=0.01,
    )
    label_to_line |= labels
    labels = plot_layer(
        G.get_layer(spark_dsg.DsgLayers.OBJECTS), node_color="c", alpha=alpha
    )
    label_to_line |= labels
    labels = plot_frontiers(G, plot_edges=True)
    label_to_line |= labels
    plot_interlayer_edges(
        G,
        spark_dsg.DsgLayers.TRAVERSABILITY,
        spark_dsg.DsgLayers.OBJECTS,
        edge_color="k",
        alpha=alpha,
    )
    return label_to_line


def plot_state(G: spark_dsg.SceneGraph, agent_state: SimulationState):
    n = G.get_node(agent_state.current_node)
    pos = n.attributes.position
    plt.scatter(*pos[:2], color="c", marker="*", s=600)
