"""Métricas sobre os registros de observability_requests, portadas do projeto de IA (somente leitura)."""
import math

from app.settings import assumptions

# resolved é um proxy: sucesso sem bloqueio do guardrail, não confirmação do usuário.


def percentile(values, pct):
    """Nearest-rank: menor valor que cobre pct% das amostras."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = math.ceil(pct / 100 * len(ordered)) - 1
    return float(ordered[min(max(index, 0), len(ordered) - 1)])


def latency(values):
    return {"avg": round(sum(values) / len(values), 1) if values else 0.0,
            "p50": round(percentile(values, 50), 1), "p95": round(percentile(values, 95), 1)}


def roi(resolutions, cost_usd, support_cost=None):
    """ROI = (economia de atendimento - custo de IA) / custo de IA."""
    support = assumptions()["support_cost_per_resolution_usd"] if support_cost is None else support_cost
    if cost_usd <= 0:
        return None
    return round((resolutions * support - cost_usd) / cost_usd, 4)


def summarize(records):
    total = len(records)
    errors = sum(1 for r in records if r.get("outcome") == "error")
    resolutions = sum(1 for r in records if r.get("resolved"))
    cost = sum(r.get("cost_usd", 0.0) for r in records)
    total_lat = latency([r["total_ms"] for r in records])
    error_rate = errors / total if total else 0.0
    ass = assumptions()
    nodes, agents = {}, {}
    for r in records:
        for name, ms in r.get("nodes_ms", {}).items():
            nodes.setdefault(name, []).append(ms)
        for name, ms in r.get("agents_ms", {}).items():
            agents.setdefault(name, []).append(ms)
    ok = total_lat["p95"] <= ass["latency_p95_limit_ms"] and error_rate <= ass["error_rate_limit"]
    return {
        "requests": total,
        "error_rate": round(error_rate, 4),
        "latency_total_ms": total_lat,
        "latency_by_node_ms": {k: latency(v) for k, v in nodes.items()},
        "latency_by_agent_ms": {k: latency(v) for k, v in agents.items()},
        "cost_usd": round(cost, 6),
        "cost_per_request_usd": round(cost / total, 6) if total else 0.0,
        "cost_p95_per_request_usd": round(percentile([r.get("cost_usd", 0.0) for r in records], 95), 6) if records else None,
        "resolutions": resolutions,
        "resolution_rate": round(resolutions / total, 4) if total else 0.0,
        "cost_per_resolution_usd": round(cost / resolutions, 6) if resolutions else None,
        "roi": roi(resolutions, cost),
        "slo": {"latency_p95_limit_ms": ass["latency_p95_limit_ms"], "error_rate_limit": ass["error_rate_limit"],
                "ok": ok if total else None},
        "resolved_is_proxy": True,
    }


def project(summary, users_list=(100, 1000)):
    """Custo e ROI por semana/mês para N usuários, a partir do custo médio real por pergunta."""
    ass = assumptions()
    questions = ass["questions_per_user_per_week"]
    rate = summary.get("resolution_rate") or 0.0
    scenarios = (("base", summary.get("cost_per_request_usd")), ("pessimista", summary.get("cost_p95_per_request_usd")))
    rows = []
    for scenario, per_request in scenarios:
        for users in users_list:
            known = questions is not None and per_request is not None
            requests = users * questions if known else None
            week = requests * per_request if known else None
            resolved = requests * rate if known else None
            rows.append({
                "scenario": scenario, "users_per_week": users,
                "requests_per_week": round(requests) if known else None,
                "cost_week_usd": round(week, 4) if known else None,
                "cost_month_usd": round(week * 52 / 12, 4) if known else None,
                "cost_week_brl": round(week * ass["usd_to_brl"], 2) if known else None,
                "roi": roi(round(resolved), week) if known and week else None,
            })
    return rows


def series(records, limit=200):
    return [{"at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
             "total_ms": r["total_ms"], "cost_usd": r.get("cost_usd", 0.0)} for r in records[-limit:]]
