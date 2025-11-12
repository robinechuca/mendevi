#!/usr/bin/env python3

"""All the available fields."""

import ast
import inspect

from mendevi.database.meta import get_extractor


def extract_labels() -> list[str]:
    """Retrieve label's name by analysing the source code of the get_label_extractor function."""
    tree = ast.parse(inspect.getsource(get_extractor))
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Match) and n.subject.id == "name"]
    assert len(nodes) == 1, "the function get_label_extractor must contains one ``match name:``"
    node = nodes.pop()
    labels = []
    for match_case in node.cases:
        labels.extend(
            [n.value for n in ast.walk(match_case.pattern) if isinstance(n, ast.Constant)],
        )
    return labels


LABELS = extract_labels()
