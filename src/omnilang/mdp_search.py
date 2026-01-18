from omnilang.mdp_states import State, Fact, PartialState
from omnilang.mdp_actions import ground_actions


def compute_preimage(state, action):
    # Compute the preimage such that action(preimage) -> state

    # 1. Bind (lifted) effects to state
    # 2. evaluate preconditions for that value of formal parameters
    # 3. Add those preconditions to state, remove the effects from the state
    pass


def update_state(state: State, added_facts: list[Fact], deleted_facts: list[Fact]):
    new_state = State({s for s in state.facts})
    for af in added_facts:
        new_state.add_fact(af)
    for df in deleted_facts:
        new_state.remove_fact(df)
    return new_state


def update_partial_state(
    state: PartialState, added_facts: list[Fact], deleted_facts: list[Fact]
):
    pass


def iterate_neighbors(actions, symbols, state):
    for a in ground_actions(actions, symbols):
        # 1. Filter for applicable actions (TODO: we can add some logic that lets us greatly reduce th  e size of ground_actions)
        if a.precondition in state:
            # 2. Apply action
            new_state = update_state(state, a.positive_effect, a.negative_effect)
            yield a, new_state


def forward_search(actions, symbols, s0, goal, max_depth=3):
    def search(max_depth, state, current_depth):
        if current_depth == max_depth:
            return None
        for action, neighbor in iterate_neighbors(actions, symbols, state):
            if goal in neighbor:
                return [action]

            rest = search(max_depth, neighbor, current_depth + 1)
            if rest is not None:
                return [action] + rest

    # Iterative deepening
    for md in range(1, max_depth):
        result = search(md, s0, 0)
        if result is not None:
            return result
    # failed to plan at max depth
