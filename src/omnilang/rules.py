from omnilang.mdp_states import Fact


def apply_transitive_frontier_rule(facts):
    connected_facts = [f for f in facts if f.head == "connected"]
    print("connected facts: ", connected_facts)
    frontiers = [f.body[0] for f in facts if f.head == "frontier"]
    print("frontiers: ", frontiers)

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

    for c1 in connected_facts:
        f1, o1 = frontier_other_from_connected(c1)
        for c2 in connected_facts:
            f2, o2 = frontier_other_from_connected(c2)
            if f1 == f2 and o1 != o2:
                new_connection = Fact("connected", [o1, o2])
                facts.add(new_connection)


def apply_rules(facts):
    # want to apply rule e.g. (connected p1 f1) (connected f1 p2) -> (connected p1 p2)
    # TODO: generalize...
    apply_transitive_frontier_rule(facts)
