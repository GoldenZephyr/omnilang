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
        return self.dsg_context[symbol.identifier.lower()]

    def get_object_type(self, o):
        print(f"WARNING: Tried to look up type for object {o} in base dsg env")
        # raise NotImplementedError(
        #    "Currently you can't rely on the base DSG environment to get symbol types"
        # )
        return None

    def get_objects_of_type(self, t):
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
        return self.dsg.find_node(
            spark_dsg.NodeSymbol(symbol.identifier[0], int(symbol.identifer[1:]))
        ) is not None or self.dsg.find_node(
            spark_dsg.NodeSymbol(
                symbol.identifier[0].upper(), int(symbol.identifer[1:])
            )
        )


@dataclass
class Environment:
    parent_environment: Optional[Environment | DsgEnvironment]
    symbols: list
    symbol_to_type: dict

    def __post_init__(self):
        self.symbol_to_metadata = {}
        self.metadata_to_symbols = {}
        self.type_to_symbols = {}
        for s, t in self.symbol_to_type.items():
            if t not in self.type_to_symbols:
                self.type_to_symbols[t] = []
            self.type_to_symbols[t].append(s)

    def get_object_type(self, o):
        if o in self.symbol_to_type:
            return self.symbol_to_type[o]
        else:
            if self.parent_environment is not None:
                return self.parent_environment.get_object_type(o)
            print(f"WARNING: No type for symbol {o}")
            return None

    def get_objects_of_type(self, t):
        objects = self.type_to_symbols.get(t, [])
        if self.parent_environment is not None:
            parent_objects = self.parent_environment.get_objects_of_type(t)
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

    def attach_metadata(self, symbol, symbol_data: dict[str, Any]):
        # TODO: Can we attach metadata in this environment to a symbol in an ancestor environment?
        self.symbol_to_metadata[symbol] = symbol_data
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
