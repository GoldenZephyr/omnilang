from omnilang.mdp_states import Environment, Symbol, State
from omnilang.streams import (
    Stream,
    GroundedStream,
    group_facts_by_symbol,
    add_facts_to_state,
    get_symbol_to_type,
)
from typing import Callable
import copy


def get_symbol_deps(env, symbol):
    heritage = get_symbol_heritage(env, symbol)

    def flatten_heritage(h):
        if h[1] is None:
            return set()
        dependencies = set()
        for d in h[1][1]:
            dependencies.add(d[0])
            deps = flatten_heritage(d)
            dependencies.update(deps)
        return dependencies

    return flatten_heritage(heritage)


def get_symbol_heritage(env, symbol):
    def get_heritage(s):
        m = env.get_metadata_for_symbol(s)
        if "generator" not in m:
            return (s, None)
        else:
            arg_heritages = ()
            args = m["generator"].inputs
            for a in args:
                arg_heritages += (get_heritage(a),)
            heritage = (m["generator"], arg_heritages)
            return (s, heritage)

    return get_heritage(symbol)


def get_streams_for_symbol(env: Environment, s: Symbol):
    heritage = get_symbol_heritage(env, s)

    def heritage_to_streams(h: tuple[Symbol, tuple]):
        # h = (Symbol, H)
        # H = (stream, (h1, ..., hN))
        S, H = h
        if H is None:
            return []
        stream_list = []
        stream, hs = H
        for hi in hs:
            streams = heritage_to_streams(hi)
            for s in streams:
                if s not in stream_list:
                    stream_list.append(s)
        if stream not in stream_list:
            stream_list.append(stream)
        return stream_list

    return heritage_to_streams(heritage)


# NOTE: this is pretty similar to expand streams, although the remapping logic here is kind of hairy.
# But it would be nice to combine some of the shared functionality if possible
def reapply_streams(
    old_env: Environment,
    env: Environment,
    stream_defs: dict[str, Stream],
    streams: list[GroundedStream],
    state: State,
    remapping_function: Callable[[Symbol], Symbol],
):
    state = copy.deepcopy(state)
    new_symbols = ()
    new_symbols_to_type = {}
    new_symbol_metadata = []

    applied_stream = True
    while applied_stream:
        applied_stream = False
        streams_next = []
        for s in streams:
            # 1. remap args
            remapped_args = []
            skip = False
            for a in s.inputs:
                previously_generated = "generator" in old_env.get_metadata_for_symbol(a)
                r = remapping_function(a)
                if previously_generated:
                    if r is not None:
                        # previously generated, now base
                        remapped_arg = r
                    else:
                        remapped_arg = a
                else:
                    if r is None:
                        # previously base, now gone
                        remapped_arg = None
                        skip = True
                    else:
                        # previously base, now base
                        remapped_arg = r
                remapped_args.append(remapped_arg)
            if skip:
                continue
            # 2. bind stream precondition to remapped args
            # 3. Check if stream precondition is satisfied by state
            #       If yes, apply stream
            #       If no, add to streams_next
            # NOTE: This will not necessarily work for non-monotonic streams
            #       To handle non-monotonic streams, we probably want to explicitly store the previous topological order
            lifted_stream = stream_defs[s.name]
            symbol_to_facts = group_facts_by_symbol(state.facts)
            if lifted_stream.is_applicable(remapped_args, symbol_to_facts):
                applied_stream = True
                new_grounded_stream, symbol_metadata = lifted_stream.apply(
                    remapped_args, env, grounded_outputs=s.output_symbols
                )

                ns = new_grounded_stream.output_symbols
                new_facts = new_grounded_stream.output_facts
                for m in symbol_metadata.values():
                    m["generator"] = new_grounded_stream

                new_symbol_metadata.append(symbol_metadata)

                domain = None
                new_symbols_to_type |= get_symbol_to_type(domain, State(new_facts))

                state = add_facts_to_state(new_facts, state)
                new_symbols = new_symbols + ns
            else:
                streams_next.append(s)

        streams = streams_next

    new_env = Environment(env, new_symbols, new_symbols_to_type)
    for nsm in new_symbol_metadata:
        for s, m in nsm.items():
            new_env.attach_metadata(s.identifier, m)

    return new_env, state
