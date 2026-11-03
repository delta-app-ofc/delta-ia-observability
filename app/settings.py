"""Configuração por variáveis de ambiente; nenhum segredo vai para o repositório."""
import os


def _float(name, default):
    return float(os.getenv(name) or default)


def assumptions():
    return {
        "support_cost_per_resolution_usd": _float("OBS_SUPPORT_COST_USD", 1.0),
        "questions_per_user_per_week": _float("OBS_QUESTIONS_PER_USER_WEEK", 0) or None,
        "usd_to_brl": _float("OBS_USD_TO_BRL", 5.5),
        "latency_p95_limit_ms": _float("OBS_LATENCY_P95_LIMIT_MS", 30000),
        "error_rate_limit": _float("OBS_ERROR_RATE_LIMIT", 0.05),
    }


def mongo_settings():
    return os.getenv("MONGO_URI"), os.getenv("MONGO_DB", "db_delta_app")
