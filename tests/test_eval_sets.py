"""Accuracy gates on the labelled sets. The blind set is a regression floor, not a target to tune towards."""
import io
import os
import sys

import pytest

import core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _both(name):
    stats, _ = core.eval_rows(os.path.join(ROOT, name))
    c, u, b, n = stats["ALL"]
    return b / n


@pytest.mark.parametrize("name", ["test_complaints.csv", "holdout_complaints.csv"])
def test_rules_accuracy_on_developer_sets(name):
    assert _both(name) >= 0.9


def test_blind_set_does_not_regress_below_frozen_baseline():
    # Frozen baseline (rules only, written before any tuning): 27/43 = 62.8% category+urgency.
    assert _both("blind_complaints.csv") >= 0.62


def test_evaluate_prints_unicode_misses_on_legacy_console(tmp_path, monkeypatch):
    csv_path = tmp_path / "unicode_complaint.csv"
    csv_path.write_text(
        "text,language,category,urgency\nನನ್ನ ಖಾತೆಯಲ್ಲಿ ಮೋಸ ನಡೆದಿದೆ,Kannada,Invalid,Invalid\n",
        encoding="utf-8",
    )
    output = io.BytesIO()
    stream = io.TextIOWrapper(output, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)

    core.evaluate(str(csv_path))

    stream.flush()
    assert b"\\u" in output.getvalue()
