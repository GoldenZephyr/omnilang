from lark import Lark, Transformer
from importlib.resources import as_file, files
import omnilang.lark
from omnilang.streams import Stream, DerivedStreamFacts
from omnilang.mdp_states import Fact, Symbol, NegatedFact, negate, TypedSymbol


class StreamTransformer(Transformer):
    def start(self, streams):
        # start -> stream_file
        return streams[0]

    def stream_file(self, stream_file_elements):
        streams = []
        derived_stream_facts = []
        for s in stream_file_elements:
            match s:
                case Stream():
                    streams.append(s)
                case DerivedStreamFacts():
                    derived_stream_facts.append(s)
                case _:
                    raise Exception(f"Unknown type {type(s)}")
        return streams, derived_stream_facts

    def parse_stream_fields(self, fields):
        d = {}
        for f in fields:
            match f:
                case ("inputs", inp, res):
                    d["params"] = inp
                    d["restrictions"] = res
                case ("outputs", out, res):
                    d["formal_outputs"] = out
                    d["output_restrictions"] = res
                case ("domain", dom):
                    d["domain"] = dom
                case ("certified", cert):
                    d["certificates"] = cert
        return d

    def stream_def(self, items):
        # items: [name, field1, field2, ...]
        name = items[0]
        fields = items[1:]

        field_values = self.parse_stream_fields(fields)
        return Stream(name=name, **field_values)

        # print("name:", name)
        # print("fields:", fields)

        # inputs = None
        # outputs = None
        # domain = None
        # certificates = None
        # restrictions = None
        # output_restrictions = None

        # for f in fields:
        #    match f:
        #        case ("inputs", inp, res):
        #            inputs = inp
        #            restrictions = res
        #        case ("outputs", out, res):
        #            outputs = out
        #            output_restrictions = res
        #        case ("domain", d):
        #            domain = d
        #        case ("certified", cert):
        #            certificates = cert
        #        case _:
        #            raise Exception(f"Encountered unexpected field: {f}")

        # return Stream(
        #    name=name,
        #    params=inputs,
        #    domain=domain,
        #    formal_outputs=outputs,
        #    certificates=certificates,
        #    restrictions=restrictions,
        #    output_restrictions=output_restrictions,
        # )

    def derived_def(self, items):
        name = items[0]
        fields = items[1:]

        field_values = self.parse_stream_fields(fields)
        return DerivedStreamFacts(name=name, **field_values)

    def stream_field(self, items):
        return items[0]

    # ---------- stream fields ----------

    def inputs(self, items):
        parms = [i[0] for i in items[0]]
        restrictions = [[i[1]] if i[1] is not None else [] for i in items[0]]  # type
        return ("inputs", parms, restrictions)

    def outputs(self, items):
        parms = [i[0] for i in items[0]]
        restrictions = [[i[1]] if i[1] is not None else None for i in items[0]]  # type
        return ("outputs", parms, restrictions)

    def domain(self, items):
        d = items[0]
        if not isinstance(d, list):
            d = [d]
        return ("domain", d)

    def certified(self, items):
        return ("certified", items[0])

    # ---------- expressions ----------

    # def logical_expr(self, items):
    #    # Either a single predicate or an AND list
    #    return items[0]

    def predicate(self, items):
        name = items[0]
        args = items[1:]
        return Fact(name, args)

    def var_list(self, items):
        return items

    def variable(self, items):
        return Symbol(items[0])

    def term(self, items):
        return items[0]

    # ---------- tokens ----------

    def NAME(self, token):
        return str(token)

    def VAR(self, token):
        return str(token)

    # ---------- AND handling ----------

    def negation(self, items):
        expression = items[0]
        if len(expression) > 1:
            raise ValueError("Currently you can only negate an atomic Fact")
        match expression[0]:
            case Fact():
                return negate(expression[0])
            case NegatedFact():
                return negate(expression[0])
            case _:
                raise ValueError(
                    f"Currently you can only negate facts, not formulas (tried to negate {expression[0]}"
                )

    def and_expr(self, items):
        result = []
        for item in items:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)
        return result

    def logical_expr(self, items):
        if isinstance(items[0], Fact):
            return [items[0]]
        return items[0]

    def empty(self, items):
        return []

    def taggable_var(self, items):
        match items[0]:
            case Symbol():
                return (items[0], None)
            case TypedSymbol():
                return (Symbol(items[0].identifier), items[0].type)
            case _:
                raise Exception(f"Unknown taggable_var {items[0]}")

    def typed_var(self, items):
        return TypedSymbol(items[0].identifier, items[1])


def parse_stream_file(fn) -> list[Stream]:
    with as_file(files(omnilang.lark).joinpath("streams.lark")) as path:
        with open(path, "r") as fo:
            stream_grammar = fo.read()

    stream_parser = Lark(
        stream_grammar,
    )

    T = StreamTransformer()

    with open(fn, "r") as fo:
        streams = fo.read()

    tree = stream_parser.parse(streams)
    streams = T.transform(tree)
    return streams


if __name__ == "__main__":
    streams = parse_stream_file("streams.pddl")
    print("Streams: ")
    print(streams)
