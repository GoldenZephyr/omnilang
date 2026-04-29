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
from matplotlib.patches import Rectangle

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


def plot_generated_connections(
    env: oml.Environment, state: oml.State, connection_predicates: list[str], color="k"
):
    def is_generated(s: oml.Symbol):
        return "generator" in env.get_metadata_for_symbol(s)

    def has_generated_symbol(f: oml.Fact):
        return any(is_generated(s) for s in f.body)

    for f in state.facts:
        if f.head not in connection_predicates:
            continue
        if not has_generated_symbol(f):
            continue
        assert (
            len(f.body) == 2
        ), f"Not sure how to plot connection fact {f} with more than two symbols"

        x1, y1 = env.get_metadata_for_symbol(f.body[0])["position"][:2]
        x2, y2 = env.get_metadata_for_symbol(f.body[1])["position"][:2]
        plt.plot([x1, x2], [y1, y2], color=color)


def plot_generated_env(
    env: oml.Environment, state: oml.State, type_to_marker: dict, plot_labels=True
):
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
                if plot_labels:
                    text_offset = 0
                    alpha = 1.0
                    x, y, _ = pos
                    plt.text(
                        x + text_offset, y + text_offset, symbol.identifier, alpha=alpha
                    )
            else:
                print("Not position for: ", symbol)

        positions = np.array(positions)
        if len(positions) == 0:
            continue
        s = plt.scatter(*positions.T, marker=marker, s=400, alpha=0.8)
        label_to_line["predicted-" + type] = s

    plot_generated_connections(env, state, ["connected", "place-in-region", "obj-at"])

    return label_to_line


def plot_rectangle(anchor, width, height, ax=None, rect_color="g", rect_linewidth=2):
    if ax is None:
        ax = plt.gca()

    # Plot bounding rectangle
    rect = Rectangle(
        anchor,
        width,
        height,
        linewidth=rect_linewidth,
        edgecolor=rect_color,
        facecolor="none",
    )
    ax.add_patch(rect)


def plot_rooms(G, edge_color, alpha=1, edge_lw=3):
    for room_node in G.get_layer(spark_dsg.DsgLayers.ROOMS).nodes:
        child_positions = np.array(
            [G.get_node(c).attributes.position for c in room_node.children()]
        )
        if len(child_positions) < 2:
            continue

        mins = np.min(child_positions, axis=0)
        maxes = np.max(child_positions, axis=0)
        width = maxes[0] - mins[0]
        height = maxes[1] - mins[1]
        plot_rectangle(
            mins - 0.1,
            width + 0.2,
            height + 0.2,
            rect_color=edge_color,
            rect_linewidth=edge_lw,
        )


def plot_dsg(
    G: spark_dsg.DynamicSceneGraph,
    alpha=1,
    trav_layer_name=spark_dsg.DsgLayers.TRAVERSABILITY,
):
    label_to_line = {}
    labels = plot_layer(
        G.get_layer(trav_layer_name),
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

    # plot_interlayer_edges(
    #     G,
    #     spark_dsg.DsgLayers.TRAVERSABILITY,
    #     spark_dsg.DsgLayers.ROOMS,
    #     edge_color="y",
    #     alpha=alpha,
    # )

    labels = plot_layer(
        G.get_layer(spark_dsg.DsgLayers.ROOMS),
        alpha=alpha,
        edge_color="k",
        node_color="g",
        edge_lw=2,
        text_offset=0.1,
    )
    label_to_line |= labels

    plot_rooms(G, edge_color="g", edge_lw=3, alpha=alpha)
    return label_to_line


def plot_state(G: spark_dsg.SceneGraph, agent_state: SimulationState):
    n = G.get_node(agent_state.current_node)
    pos = n.attributes.position
    plt.scatter(*pos[:2], color="c", marker="*", s=600)
