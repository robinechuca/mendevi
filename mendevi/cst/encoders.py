#!/usr/bin/env python3

"""All the available encoders."""

import ast
import inspect

from mendevi.encode import get_transcode_cmd


def extract_encoders() -> list[str]:
    """Retrieve encoders names by analysing the source code of the get_transcode_cmd function."""
    tree = ast.parse(inspect.getsource(get_transcode_cmd))
    nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Match) and isinstance(n.subject, ast.Subscript)
        and (n.subject.value.id, n.subject.slice.value) == ("kwargs", "encoder")
    ]
    assert len(nodes) == 1, 'the function get_transcode_cmd must contains one ``match kwargs["encoder"]:``'
    node = nodes.pop()
    labels = []
    for match_case in node.cases:
        labels.extend(
            [n.value for n in ast.walk(match_case.pattern) if isinstance(n, ast.Constant)],
        )
    return labels


ENCODERS = set(extract_encoders())
