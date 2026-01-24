from omnilang.mdp_states import Fact


def apply_transitive_frontier_rule(facts):
    connected_facts = [f for f in facts if f.head == "connected"]
    frontiers = set([f.body[0] for f in facts if f.head == "frontier"])

    def frontier_other_from_connected(fact):
        arg1_frontier = fact.body[0] in frontiers
        arg2_frontier = fact.body[1] in frontiers
        if arg1_frontier:
            if arg2_frontier:
                return None, None
            return fact.body[0], fact.body[1]
        if arg2_frontier:
            return fact.body[1], fact.body[0]
        return None, None

    frontier_connections = []
    for cf in connected_facts:
        frontier_other = frontier_other_from_connected(cf)
        frontier_connections.append(frontier_other)

    for idx in range(len(frontier_connections)):
        f1, o1 = frontier_connections[idx]
        for jdx in range(idx + 1, len(frontier_connections)):
            f2, o2 = frontier_connections[jdx]
            if f1 == f2 and o1 != o2:
                new_connection = Fact("connected", [o1, o2])
                facts.add(new_connection)


def apply_rules(facts):
    # want to apply rule e.g. (connected p1 f1) (connected f1 p2) -> (connected p1 p2)
    # TODO: generalize...
    apply_transitive_frontier_rule(facts)
