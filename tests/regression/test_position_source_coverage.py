"""Regression: src/ altında her Position(...) constructor source kwarg set ediyor mu?

Yan task atlama riski koruması (SPEC-AUDIT-001 Task 2). Gelecekte yeni Position
constructor eklenirse + source unutulursa bu test FAIL eder.

Position(**dict_expansion) çağrıları muaftır — pos_data dict'i field içerir
veya Position model'inin default'unu (source="bookmaker") kullanır.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent.parent / "src"


def _iter_position_calls():
    """src/ altındaki .py dosyalarında Position(...) çağrılarını yield et."""
    for py in SRC_ROOT.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "Position":
                continue
            # Position class definition'ı muaf (BaseModel inheritance)
            yield py.relative_to(SRC_ROOT.parent), node


def _has_source_kwarg(node: ast.Call) -> bool:
    return any(kw.arg == "source" for kw in node.keywords)


def _is_kwarg_expansion(node: ast.Call) -> bool:
    """Position(**dict) gibi expansion çağrısı."""
    return any(kw.arg is None for kw in node.keywords)


def test_all_explicit_position_constructors_set_source():
    """Her açık (kwarg-style) Position(...) çağrısı 'source=' geçirmeli.

    **dict expansion muaf (model default veya state file field kullanılır).
    """
    missing: list[str] = []
    for path, node in _iter_position_calls():
        if _is_kwarg_expansion(node):
            continue
        if not _has_source_kwarg(node):
            missing.append(f"{path}:{node.lineno}")
    assert not missing, (
        f"Position(...) constructor 'source' kwarg eksik: {missing}\n"
        f"Düzeltme: her constructor'a source=signal.source veya 'model'/'bookmaker' ekle."
    )
