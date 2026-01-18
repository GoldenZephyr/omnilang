from lark import Lark, Transformer
from importlib.resources import as_file, files
import omnilang
from omnilang.streams import Stream
from omnilang.mdp_states import Fact, Symbol


class StreamTransformer(Transformer):
    def start(self, streams):
        # start -> stream_file
        return streams[0]

    def stream_file(self, streams):
        return streams

    def stream_def(self, items):
        # items: [name, field1, field2, ...]
        name = items[0]
        fields = items[1:]

        inputs = None
        outputs = None
        domain = None
        certificates = None

        for key, value in fields:
            if key == "inputs":
                inputs = value
            elif key == "outputs":
                outputs = value
            elif key == "domain":
                domain = value
            elif key == "certified":
                certificates = value

        return Stream(
            name=name,
            params=inputs,
            domain=domain,
            formal_outputs=outputs,
            certificates=certificates,
        )

    def stream_field(self, items):
        return items[0]

    # ---------- stream fields ----------

    def inputs(self, items):
        return ("inputs", items[0])

    def outputs(self, items):
        return ("outputs", items[0])

    def domain(self, items):
        return ("domain", items[0])

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


def parse_stream_file(fn):
    with as_file(files(omnilang).joinpath("streams.lark")) as path:
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
    # with open("streams.lark", "r") as fo:
    #    stream_grammar = fo.read()

    # stream_parser = Lark(
    #    stream_grammar,
    # )

    # T = StreamTransformer()

    # with open("streams.pddl", "r") as fo:
    #    example_streams = fo.read()

    # tree = stream_parser.parse(example_streams)
    # output = T.transform(tree)

    streams = parse_stream_file("streams.pddl")
    print("Streams: ")
    print(streams)
