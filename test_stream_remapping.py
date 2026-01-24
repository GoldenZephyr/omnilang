from omnilang.test_planner import load_full_domain
from omnilang.mdp_states import Environment, State, Fact, Symbol
from omnilang.streams import (
    expand_streams,
    GroundedStream,
)
from typing import Callable, Optional

from omnilang.stream_tracking import get_streams_for_symbol, reapply_streams


# This might be useful, but actually we probably just want to
# reapply the previous grounded streams from s0 to the extent possible
def compute_remapped_generated_symbols(
    new_env: Environment,
    old_env: Environment,
    old_symbols: list[Symbol],
    symbol_remapper: Callable[[Symbol], Optional[Symbol]],
):
    # (old_symbol, old_heritage) -> (new_symbol, new_heritage)
    def remap(old_symbol) -> tuple[Symbol, tuple]:
        m = old_env.get_metadata_for_symbol(old_symbol)
        old_symbol_was_generated = "generator" in m
        new_symbol = symbol_remapper(old_symbol)
        if not old_symbol_was_generated:
            if new_symbol is None:
                # Symbol was deleted
                return None
            # New symbol (still) has "Base" heritage
            return (new_symbol, None)

        if new_symbol is not None:
            # Here, the symbol was previously generated but we have now
            # associated it with a Base symbol
            return (new_symbol, None)

        # Here, the old symbol was generated. We want to return a symbol with
        # updated heritage, if the heritage still exists
        generator: GroundedStream = m["generator"]
        remapped_args = ()
        for a in generator.inputs:
            print("a: ", a)
            remapped_arg = remap(a)
            if remapped_arg is not None:
                remapped_args += remapped_arg
            else:
                return None
        return (old_symbol, remapped_args)

    new_symbols_with_heritage = [remap(o) for o in old_symbols]
    return new_symbols_with_heritage


if __name__ == "__main__":
    stream_path = "streams_remapping.pddl"
    pddl_domain_path = "pick_domain.pddl"
    domain = load_full_domain(pddl_domain_path, stream_path)

    facts = set([Fact("obj", [Symbol("O1")]), Fact("place", [Symbol("p1")])])

    s0 = State(facts)

    symbols = list(map(Symbol, ["O1", "p1"]))
    symbol_to_type = {}
    symbol_to_type[Symbol("O1")] = "obj"
    symbol_to_type[Symbol("p1")] = "place"

    env = Environment(None, symbols, symbol_to_type)

    generated_env, generated_s0 = expand_streams(
        env,
        [domain.streams[1]],
        s0,
        stream_evals_per_level=1,
    )

    generated_env2, generated_s02 = expand_streams(
        generated_env,
        [domain.streams[2]],
        generated_s0,
        stream_evals_per_level=1,
    )

    facts1 = [Fact("obj", [Symbol("O1")]), Fact("place", [Symbol("p2")])]
    s1 = State(set(facts1))

    symbols1 = list(map(Symbol, ["O1", "p2"]))
    symbol_to_type1 = {}
    symbol_to_type1[Symbol("O1")] = "obj"
    symbol_to_type1[Symbol("p2")] = "place"

    env1 = Environment(None, symbols1, symbol_to_type1)

    def symbol_remapping(s: Symbol):
        assert isinstance(s, Symbol)
        remapping_old_to_new = {"p1": "p2", "O1": "O1"}
        if s.identifier in remapping_old_to_new:
            return Symbol(remapping_old_to_new[s.identifier])
        else:
            return None

    new_symbols = compute_remapped_generated_symbols(
        env1,
        generated_env2,
        [Symbol("s1")],
        symbol_remapping,
    )

    streams_to_reapply = get_streams_for_symbol(generated_env2, Symbol("s1"))
    stream_lookup = {s.name: s for s in domain.streams}

    new_env, new_state = reapply_streams(
        generated_env2,
        env1,
        stream_lookup,
        streams_to_reapply,
        s1,
        symbol_remapping,
    )
