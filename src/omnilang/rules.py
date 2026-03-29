from omnilang.mdp_states import Fact, State
from omnilang.streams import DerivedStreamFacts, group_facts_by_symbol
from omnilang.environment import Environment
import copy
from typing import Any


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
                new_connection = Fact("connected", [o2, o1])
                facts.add(new_connection)


def merge_dict_of_lists(
    dol1: dict[Any, list], dol2: dict[Any, list], inplace: bool = False
):
    if inplace:
        d = dol1
    else:
        d = copy.deepcopy(dol1)
    for k, v in dol2.items():
        if k in d:
            d[k] += v
        else:
            d[k] = v
    return d


def apply_rules_iter(rules: list[DerivedStreamFacts], env: Environment, state: State):
    added_facts = False
    for rule in rules:
        print("Processing: ", rule.name)
        symbol_to_facts = group_facts_by_symbol(state.facts)
        applicable_args = rule.get_applicable_args(symbol_to_facts, env, state)

        print("Applicable args: ", applicable_args)
        for idx, a in enumerate(applicable_args):
            if not rule.is_applicable(a, symbol_to_facts, env):
                # shouldn't hit this for monotonic streams, but for
                # nonmonotonic streams a binding that was previously
                # possible might become invalid by the time we process it.
                print("WARNING: nonmonotonic stream detected (?)")
                continue
            new_facts = rule.apply(a, environment=env)
            if new_facts.issubset(state.facts):
                continue
            added_facts = True
            state.facts |= new_facts
            new_symbol_to_facts = group_facts_by_symbol(new_facts)
            symbol_to_facts = merge_dict_of_lists(
                symbol_to_facts, new_symbol_to_facts, inplace=True
            )
    return added_facts, state


def apply_rules(rules: list[DerivedStreamFacts], env: Environment, state: State):
    new_state = State(copy.copy(state.facts))

    # NOTE: in general we might want to apply until a fixed point. For now, we will just apply a single iteration
    # rule_applied = True
    # while rule_applied:
    #     rule_applied, new_state = apply_rules_iter(rules, env, new_state)

    rule_applied, new_state = apply_rules_iter(rules, env, new_state)

    return new_state
