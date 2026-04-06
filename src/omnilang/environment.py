from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any
from omniplanner.omniplanner import DsgContextProvider
import spark_dsg
import logging
from omnilang.mdp_states import Symbol

logger = logging.getLogger(__name__)


class DsgEnvironment:
    def __init__(self, dsg: spark_dsg.DynamicSceneGraph):
        self.dsg = dsg
        self.dsg_context = DsgContextProvider(dsg)
        self._type_hierarchy = {}

    def attach_metadata(self, symbol, symbol_data):
        self.dsg_context[symbol] = symbol_data

    def get_symbols_with_metadata(self, metadata_type: str):
        dsg_symbols = set()
        for node in self.dsg.nodes:
            nid = node.id.str()
            cxt = self.dsg_context[nid]
            if cxt is not None:
                if metadata_type in cxt:
                    dsg_symbols.add(nid.lower())
        # dsg_symbols = set(node.id.str() for node in self.dsg.nodes)
        for explicit_symbol, cxt in self.dsg_context.items():
            if metadata_type in cxt:
                dsg_symbols.add(explicit_symbol)
        return dsg_symbols

    def get_metadata_for_symbol(self, symbol: Symbol):
        assert isinstance(symbol, Symbol)
        logger.debug(f"metadata from base: {symbol}")
        try:
            return self.dsg_context[symbol.identifier.lower()]
        except KeyError:
            return {}

    def get_object_type(self, o):
        logger.debug(f"Tried to look up type for object {o} in base dsg env")
        # raise NotImplementedError(
        #    "Currently you can't rely on the base DSG environment to get symbol types"
        # )
        return None

    def get_objects_of_type(self, t, include_subtypes=True):
        return []

    def get_symbols(self) -> set:
        symbols = set()
        for node in self.dsg.nodes:
            symbol = Symbol(node.id.str().lower())
            symbols.add(symbol)
        for symbol, cxt in self.dsg_context.items():
            symbols.add(Symbol(symbol))
        return symbols

    def contains(self, symbol) -> bool:
        ns_key = symbol.identifier[0]
        ns_id = symbol.identifier[1:]
        if ns_key.isdigit() or not ns_id.isdigit():
            return None
        return self.dsg.find_node(
            spark_dsg.NodeSymbol(symbol.identifier[0], int(symbol.identifier[1:]))
        ) is not None or self.dsg.find_node(
            spark_dsg.NodeSymbol(
                symbol.identifier[0].upper(), int(symbol.identifer[1:])
            )
        )


def compute_descendant_types(type_hierarchy):
    def get_desc_types(t):
        types = set(type_hierarchy.get(t, []))
        for subtype in type_hierarchy.get(t, []):
            types |= get_desc_types(subtype)
        return types

    types = type_hierarchy.keys()
    descendant_types = {}
    for t in types:
        descendant_types[t] = []

    for supertype in types:
        descendant_types[supertype] = get_desc_types(supertype)

    return descendant_types


@dataclass
class Environment:
    parent_environment: Optional[Environment | DsgEnvironment]
    symbols: list
    symbol_to_type: dict
    _type_hierarchy: dict = None

    def __post_init__(self):
        if self.parent_environment is not None and self._type_hierarchy is None:
            self._type_hierarchy = self.parent_environment._type_hierarchy

        self._descendant_types = compute_descendant_types(self._type_hierarchy)
        self.symbol_to_metadata = {}
        self.metadata_to_symbols = {}
        self.type_to_symbols = {}
        for s, t in self.symbol_to_type.items():
            if t not in self.type_to_symbols:
                self.type_to_symbols[t] = []
            self.type_to_symbols[t].append(s)

        assert len(self._type_hierarchy) > 0

    def is_subclass(self, symbol: Symbol, type: str):
        # does symbol have a subtype of type?
        t = self.get_object_type(symbol)
        return t == type or t in self._descendant_types.get(type, [])

    def get_object_type(self, o):
        if o in self.symbol_to_type:
            return self.symbol_to_type[o]
        else:
            if self.parent_environment is not None:
                return self.parent_environment.get_object_type(o)
            print(f"WARNING: No type for symbol {o}")
            return None

    def get_subtypes_of_type(self, query_type):
        return self._descendant_types.get(query_type, [])

    def get_objects_of_type(self, query_type, include_subtypes=True):
        types = [query_type]
        if include_subtypes:
            types += self._descendant_types.get(query_type, [])

        objects = []
        for t in types:
            objects += self.type_to_symbols.get(t, [])

        if self.parent_environment is not None:
            parent_objects = self.parent_environment.get_objects_of_type(
                query_type, include_subtypes
            )
        else:
            parent_objects = []
        return objects + parent_objects

    def get_type_to_objects(self):
        if self.parent_environment is not None:
            parent_type_to_objects = self.parent_environment.get_type_to_objects()
        else:
            parent_type_to_objects = {}
        type_to_objects = self.type_to_symbols
        return type_to_objects | parent_type_to_objects

    def attach_metadata(self, symbol: Symbol, symbol_data: dict[str, Any]):
        # TODO: Can we attach metadata in this environment to a symbol in an ancestor environment?
        assert isinstance(symbol, Symbol)
        if symbol not in self.symbol_to_metadata:
            self.symbol_to_metadata[symbol] = symbol_data
        else:
            self.symbol_to_metadata[symbol] |= symbol_data
        for metadata_type, metadata_value in symbol_data.items():
            if metadata_type not in self.metadata_to_symbols:
                self.metadata_to_symbols[metadata_type] = set()
            self.metadata_to_symbols[metadata_type].add(symbol)

    def get_symbols_with_metadata(self, metadata_type: str):
        if self.parent_environment is not None:
            parent_metadata = self.parent_environment.get_symbols_with_metadata(
                metadata_type
            )
        else:
            parent_metadata = set()
        return self.metadata_to_symbols.get(metadata_type, set()) | parent_metadata

    def get_metadata_for_symbol(self, symbol: Symbol):
        assert isinstance(symbol, Symbol)
        if self.parent_environment is not None:
            parent_metadata = self.parent_environment.get_metadata_for_symbol(symbol)
        else:
            parent_metadata = {}
        metadata = self.symbol_to_metadata.get(symbol, {})
        # NOTE: Unclear if we want to equate the "planning symbol" with the "dsg symbol", even if they have the same name?
        output = {}
        for k, v in parent_metadata.items():
            output[k] = v
        for k, v in metadata.items():
            output[k] = v
        output["type"] = self.get_object_type(symbol)
        return output

    def contains(self, symbol) -> bool:
        if self.parent_environment is None:
            return symbol in self.symbols
        return symbol in self.symbols or self.parent_environment.contains(symbol)

    def get_symbols(self) -> set:
        if self.parent_environment is not None:
            parent_symbols = self.parent_environment.get_symbols()
        else:
            parent_symbols = set()
        return set(self.symbols) | parent_symbols
