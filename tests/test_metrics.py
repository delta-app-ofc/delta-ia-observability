from datetime import datetime, timezone

import pytest

from app import metrics


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("OBS_SUPPORT_COST_USD", "1.0")
    monkeypatch.setenv("OBS_QUESTIONS_PER_USER_WEEK", "5")
    monkeypatch.setenv("OBS_LATENCY_P95_LIMIT_MS", "1000")
    monkeypatch.setenv("OBS_ERROR_RATE_LIMIT", "0.5")


def rec(ms, cost, outcome="success", resolved=True):
    return {"total_ms": ms, "cost_usd": cost, "outcome": outcome, "resolved": resolved,
            "created_at": datetime(2026, 11, 1, tzinfo=timezone.utc),
            "nodes_ms": {"route": ms / 2}, "agents_ms": {"forecast": ms}}


def test_percentile_nearest_rank():
    assert metrics.percentile([10, 20, 30, 40], 50) == 20
    assert metrics.percentile([10, 20, 30, 40], 95) == 40
    assert metrics.percentile([], 95) == 0.0


def test_summary_counts_errors_and_cost():
    s = metrics.summarize([rec(100, 0.01), rec(300, 0.03), rec(200, 0.0, "error", False)])
    assert s["requests"] == 3 and s["error_rate"] == round(1 / 3, 4)
    assert s["cost_usd"] == 0.04 and s["resolutions"] == 2
    assert s["cost_per_resolution_usd"] == 0.02 and s["resolved_is_proxy"]


def test_latency_by_agent_and_node():
    s = metrics.summarize([rec(100, 0.01), rec(300, 0.01)])
    assert s["latency_by_agent_ms"]["forecast"]["p95"] == 300
    assert s["latency_by_node_ms"]["route"]["p50"] == 50


def test_roi_and_empty_cost():
    assert metrics.roi(10, 1.0) == 9.0
    assert metrics.roi(10, 0) is None


def test_slo_flags_violation():
    assert metrics.summarize([rec(500, 0.01)])["slo"]["ok"] is True
    assert metrics.summarize([rec(5000, 0.01)])["slo"]["ok"] is False


def test_projection_100_and_1000_users():
    rows = metrics.project(metrics.summarize([rec(100, 0.02)]))
    base = [r for r in rows if r["scenario"] == "base"]
    assert [r["users_per_week"] for r in base] == [100, 1000]
    assert base[0]["requests_per_week"] == 500 and base[0]["cost_week_usd"] == 10.0
    assert base[1]["cost_week_usd"] == 100.0
