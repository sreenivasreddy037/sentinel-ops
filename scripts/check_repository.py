"""Dependency-free structural checks; these do NOT replace pytest or Ruff."""

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = sorted(path for folder in ["app", "tests", "scripts", "evals"]
                     for path in (ROOT / folder).rglob("*.py"))
    for path in sources:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path), feature_version=(3, 9))
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                protected = ast.Module(body=node.body, type_ignores=[])
                assert not any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                               and call.func.id == "interrupt" for call in ast.walk(protected)), path
        for node in ast.walk(tree):
            if "app" in path.relative_to(ROOT).parts and isinstance(node, ast.Import):
                assert not any(alias.name == "subprocess" for alias in node.names), path
            if "app" in path.relative_to(ROOT).parts and isinstance(node, ast.ImportFrom):
                assert node.module != "subprocess", path
    books = sorted((ROOT / "data/runbooks").glob("*.md"))
    assert len(books) == 15
    ids = set()
    for book in books:
        content = book.read_text()
        ids.add(re.search(r"^Runbook ID: (.+)$", content, re.M)[1])
        assert content.count("\n## ") == 7, book
        assert len(content.split()) >= 350, book
    golden = json.loads((ROOT / "evals/golden_set.json").read_text())
    assert len(golden) == 20
    assert all(set(case["expected_runbook_ids"]) <= ids for case in golden)
    assert all(case["ground_truth_remediation"] for case in golden)
    print(f"PASS: {len(sources)} Python files parse; interrupt boundary verified; "
          f"{len(books)} runbooks / {len(golden)} golden cases structurally valid.")


if __name__ == "__main__":
    main()
