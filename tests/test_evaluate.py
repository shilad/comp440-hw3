"""Offline tests for what evaluate.py prints and saves around a run: its progress
lines, report.txt (which marks a finished run) and run.json."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import evaluate  # noqa: E402
import wiki  # noqa: E402

ITEMS = [{"id": f"c{i}", "claim": f"claim {i}", "source": "hover", "label": "SUPPORTED", "hops": 2}
         for i in range(12)]


def always_supported(claim):
    return {"claim": claim, "verdict": "supported", "evidence": [], "explanation": "x",
            "trace": [], "steps": 1, "tokens": {"input": 10, "output": 2}, "cost_usd": 0.001}


def run_main(monkeypatch, tmp_path):
    claims = tmp_path / "claims.jsonl"
    claims.write_text("\n".join(json.dumps(item) for item in ITEMS) + "\n")
    out_dir = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["evaluate.py", str(claims), "--methods", "agent",
                                      "--out", str(out_dir)])
    evaluate.main()
    return claims, out_dir


def test_a_run_prints_how_far_it_has_got(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(evaluate.METHODS, "agent", always_supported)
    evaluate.run_method("agent", ITEMS, tmp_path, workers=2)
    printed = capsys.readouterr().out
    assert "agent: 0 already done, running 12" in printed
    assert "agent: 10 of 12 done" in printed
    assert "agent: 12 of 12 done" in printed


def test_a_finished_run_saves_its_report(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(evaluate.METHODS, "agent", always_supported)
    claims, out_dir = run_main(monkeypatch, tmp_path)
    printed = capsys.readouterr().out
    report = (out_dir / "report.txt").read_text()
    assert "Share of claims where the verdict matched the label" in report
    assert "12/12" in report
    assert "Average per claim" in report
    assert report.strip() in printed
    assert json.loads((out_dir / "run.json").read_text()) == {"claims": str(claims)}

    # Running the same command again runs nothing and prints the same tables.
    monkeypatch.setitem(evaluate.METHODS, "agent",
                        lambda claim: pytest.fail("a saved claim was run again"))
    evaluate.main()
    assert "agent: 12 already done, running 0" in capsys.readouterr().out
    assert (out_dir / "report.txt").read_text() == report


def test_a_run_with_a_failed_claim_has_no_report(monkeypatch, tmp_path, capsys):
    def one_fails(claim):
        if claim == "claim 3":
            raise wiki.RateLimited("too many requests")
        return always_supported(claim)

    out_dir = tmp_path / "run"
    out_dir.mkdir()
    (out_dir / "report.txt").write_text("left over from an earlier run\n")
    monkeypatch.setitem(evaluate.METHODS, "agent", one_fails)
    run_main(monkeypatch, tmp_path)
    assert "run the same command again" in capsys.readouterr().out
    assert not (out_dir / "report.txt").exists()
    assert len((out_dir / "agent.jsonl").read_text().splitlines()) == 11
