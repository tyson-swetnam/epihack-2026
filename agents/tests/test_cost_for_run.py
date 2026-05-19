"""Unit tests for :func:`onehealth_agents.audit.cost_for_run`.

Pinned dollars-per-million-tokens at the time of writing:

================ ============= ============== =============== ==================
Model            input ($/Mt)  output ($/Mt)  cache_read     cache_creation
================ ============= ============== =============== ==================
Haiku 4.5        $1.00         $5.00          $0.10           $1.25
Sonnet 4.6       $3.00         $15.00         $0.30           $3.75
Opus 4.7         $15.00        $75.00         $1.50           $18.75
================ ============= ============== =============== ==================
"""

from __future__ import annotations

import math

import pytest

from onehealth_agents import cost_for_run


# --------------------------------------------------------------------------
# Canonical token counts -- chosen so the per-million-tokens math is exact.
# --------------------------------------------------------------------------
def test_haiku_1m_in_1m_out():
    # 1M input + 1M output @ Haiku rates = $1 + $5 = $6.
    cost = cost_for_run("claude-haiku-4-5", 1_000_000, 1_000_000)
    assert math.isclose(cost, 6.00, rel_tol=1e-9)


def test_sonnet_1m_in_1m_out():
    # 1M input + 1M output @ Sonnet rates = $3 + $15 = $18.
    cost = cost_for_run("claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert math.isclose(cost, 18.00, rel_tol=1e-9)


def test_opus_1m_in_1m_out():
    # 1M input + 1M output @ Opus rates = $15 + $75 = $90.
    cost = cost_for_run("claude-opus-4-7", 1_000_000, 1_000_000)
    assert math.isclose(cost, 90.00, rel_tol=1e-9)


# --------------------------------------------------------------------------
# Realistic per-call token counts (Haiku intake step + Sonnet triage step).
# --------------------------------------------------------------------------
def test_haiku_typical_intake_call():
    # 4k input, 600 output. Cost = 4000 * 1.00 / 1e6 + 600 * 5.00 / 1e6.
    cost = cost_for_run("claude-haiku-4-5", 4_000, 600)
    expected = (4_000 * 1.00 + 600 * 5.00) / 1_000_000
    assert math.isclose(cost, round(expected, 8), rel_tol=1e-9)


def test_sonnet_typical_triage_call_with_cache():
    # 10k input, 1.5k output, 8k cache_read, 2k cache_creation.
    cost = cost_for_run("claude-sonnet-4-6", 10_000, 1_500, 8_000, 2_000)
    expected = (
        10_000 * 3.00
        + 1_500 * 15.00
        + 8_000 * 0.30
        + 2_000 * 3.75
    ) / 1_000_000
    assert math.isclose(cost, round(expected, 8), rel_tol=1e-9)


# --------------------------------------------------------------------------
# Edge cases -- missing inputs collapse to zero rather than raise.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "model,prompt,completion",
    [
        (None, 1_000, 100),
        ("not-a-real-model", 1_000, 100),
        ("claude-haiku-4-5", None, None),
        ("claude-haiku-4-5", 0, 0),
    ],
)
def test_zero_cases_collapse_to_zero(model, prompt, completion):
    assert cost_for_run(model, prompt, completion) == 0.0


# --------------------------------------------------------------------------
# Env-var overrides
# --------------------------------------------------------------------------
def test_env_var_overrides_haiku_input(monkeypatch):
    monkeypatch.setenv("CLAUDE_HAIKU_INPUT_USD_PER_M", "2.50")
    # Override should now apply: 1M input * $2.50 = $2.50 (no output tokens).
    cost = cost_for_run("claude-haiku-4-5", 1_000_000, 0)
    assert math.isclose(cost, 2.50, rel_tol=1e-9)


def test_env_var_invalid_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CLAUDE_SONNET_OUTPUT_USD_PER_M", "not-a-number")
    cost = cost_for_run("claude-sonnet-4-6", 0, 1_000_000)
    # Default Sonnet output is $15/M, so 1M tokens = $15.
    assert math.isclose(cost, 15.00, rel_tol=1e-9)
