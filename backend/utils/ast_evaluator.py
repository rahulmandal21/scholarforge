"""
backend/utils/ast_evaluator.py

ScholarForge — Phase 7a: AST Structural Similarity

Compares two pieces of Python code structurally (not semantically) using
the ast module — counting classes, functions, imports, loops, and
conditionals — and returns a similarity score between 0 and 1.

This is intentionally crude: it can't tell if code is *correct*, only
whether it has a similar shape/complexity to a reference implementation.
That's enough to catch degenerate generations (e.g. an empty stub or a
single one-line function when a full class was expected).
"""

import ast

FEATURE_NODE_TYPES = {
    "num_classes": (ast.ClassDef,),
    "num_functions": (ast.FunctionDef, ast.AsyncFunctionDef),
    "num_imports": (ast.Import, ast.ImportFrom),
    "num_loops": (ast.For, ast.While),
    "num_conditionals": (ast.If,),
}


def _extract_features(code: str):
    """Parse code and count structural features. Returns None on invalid syntax."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    features = {key: 0 for key in FEATURE_NODE_TYPES}
    for node in ast.walk(tree):
        for feature_name, node_types in FEATURE_NODE_TYPES.items():
            if isinstance(node, node_types):
                features[feature_name] += 1
    return features


def compute_ast_similarity(code1: str, code2: str) -> float:
    """
    Returns a 0-1 structural similarity score between two code strings.

    0.0 means either string fails to parse as valid Python, or the
    structures are completely different. 1.0 means identical structural
    feature counts (classes, functions, imports, loops, conditionals).
    """
    features1 = _extract_features(code1)
    features2 = _extract_features(code2)

    if features1 is None or features2 is None:
        return 0.0

    per_feature_scores = []
    for key in FEATURE_NODE_TYPES:
        a, b = features1[key], features2[key]
        if a == 0 and b == 0:
            per_feature_scores.append(1.0)
        else:
            per_feature_scores.append(1 - abs(a - b) / max(a, b, 1))

    return sum(per_feature_scores) / len(per_feature_scores)


if __name__ == "__main__":
    sample_a = """
class Foo:
    def __init__(self):
        pass
    def bar(self):
        for i in range(10):
            if i > 5:
                pass
"""
    sample_b = """
class Foo:
    def __init__(self):
        pass
"""
    score = compute_ast_similarity(sample_a, sample_b)
    print(f"Similarity score: {score:.3f}")
