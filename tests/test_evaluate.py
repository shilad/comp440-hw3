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
    assert "HoVer, supported          12/12" in report   # the count split by the dataset's label
    assert "HoVer, not supported       0/0" in report
    assert "Average per claim" in report
    assert report.strip() in printed
    assert json.loads((out_dir / "run.json").read_text()) == {"claims": str(claims)}

    # Running the same command again runs nothing and prints the same tables.
    monkeypatch.setitem(evaluate.METHODS, "agent",
                        lambda claim: pytest.fail("a saved claim was run again"))
    evaluate.main()
    assert "agent: 12 already done, running 0" in capsys.readouterr().out
    assert (out_dir / "report.txt").read_text() == report


def test_saved_results_from_an_earlier_agent_are_pointed_out(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(evaluate.METHODS, "agent", always_supported)
    monkeypatch.setattr(evaluate, "agent_version", lambda: "v1")
    _, out_dir = run_main(monkeypatch, tmp_path)
    assert "earlier version" not in capsys.readouterr().out

    # The student changes instructions.md and runs the same command: nothing runs,
    # and the program says the saved results are from the earlier agent.
    monkeypatch.setattr(evaluate, "agent_version", lambda: "v2")
    monkeypatch.setitem(evaluate.METHODS, "agent",
                        lambda claim: pytest.fail("ran again without --fresh"))
    evaluate.main()
    printed = capsys.readouterr().out
    assert "earlier version of your agent" in printed and "--fresh" in printed

    # With --fresh every claim runs again with the agent as it is now.
    monkeypatch.setitem(evaluate.METHODS, "agent", always_supported)
    monkeypatch.setattr(sys, "argv", sys.argv + ["--fresh"])
    evaluate.main()
    printed = capsys.readouterr().out
    assert "agent: 0 already done, running 12" in printed
    assert "earlier version" not in printed
    rows = [json.loads(line) for line in (out_dir / "agent.jsonl").read_text().splitlines()]
    assert len(rows) == 12 and {row["agent_version"] for row in rows} == {"v2"}
    assert (out_dir / "report.txt").exists()


def test_old_and_new_results_are_not_mixed(monkeypatch, tmp_path, capsys):
    def two_fail(claim):  # a run that stopped before it finished
        if claim in ("claim 10", "claim 11"):
            raise wiki.RateLimited("too many requests")
        return always_supported(claim)

    monkeypatch.setattr(evaluate, "agent_version", lambda: "v1")
    monkeypatch.setitem(evaluate.METHODS, "agent", two_fail)
    _, out_dir = run_main(monkeypatch, tmp_path)

    monkeypatch.setattr(evaluate, "agent_version", lambda: "v2")  # then the agent changed
    monkeypatch.setitem(evaluate.METHODS, "agent",
                        lambda claim: pytest.fail("mixed old and new results"))
    with pytest.raises(SystemExit) as stopped:
        evaluate.main()
    assert "earlier version of your agent" in str(stopped.value)
    assert "--fresh" in str(stopped.value)
    assert len((out_dir / "agent.jsonl").read_text().splitlines()) == 10


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


def test_lookup_with_no_log_prints_but_does_not_add_to_the_record(monkeypatch, tmp_path, capsys):
    import lookup
    monkeypatch.setattr(lookup, "load_dotenv", lambda: None)  # leave your own .env alone
    monkeypatch.setattr(lookup, "LOG", tmp_path / "lookups.jsonl")
    monkeypatch.setattr(wiki, "read", lambda title, section=None: f"Page: {title}")
    monkeypatch.setattr(sys, "argv", ["lookup.py", "--no-log", "read", "Saint Paul, Minnesota"])
    lookup.main()
    printed = capsys.readouterr().out
    assert "Page: Saint Paul, Minnesota" in printed
    assert "lookups.jsonl" not in printed
    assert not (tmp_path / "lookups.jsonl").exists()


def test_a_reply_with_unescaped_quote_marks_keeps_its_verdict():
    import baselines
    reply = ('{"verdict": "doesn\'t say", "explanation": "The text names the composer of '
             '"Persian Surgery Dervishes" but does not give his birthday."}')
    with pytest.raises(json.JSONDecodeError):
        json.loads(reply)  # this is the kind of reply that used to lose its verdict
    verdict, explanation = baselines._parse(reply)
    assert verdict == "doesn't say"
    assert explanation == ('The text names the composer of "Persian Surgery Dervishes" '
                           "but does not give his birthday.")


def test_a_reply_that_is_valid_json_is_read_as_before():
    import baselines
    fenced = '```json\n{"verdict": "refuted", "explanation": "The page says 1940."}\n```'
    assert baselines._parse(fenced) == ("refuted", "The page says 1940.")
    other_order = '{"explanation": "The page says "1935".", "verdict": "supported"}'
    assert baselines._parse(other_order) == ("supported", 'The page says "1935".')


def test_a_reply_with_no_verdict_still_gives_none():
    import baselines
    assert baselines._parse("I can't help with that.") == (None, "I can't help with that.")
    assert baselines._parse('{"verdict": "maybe", "explanation": "x"}') == (None, "x")
