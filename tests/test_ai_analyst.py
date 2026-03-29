import json, pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.models import MarketData
from src.config import AIConfig
import src.ai_analyst as ai_analyst_mod
from src.ai_analyst import AIAnalyst, BUDGET_FILE


@pytest.fixture(autouse=True)
def clean_budget_file():
    """Remove budget file before/after each test."""
    if BUDGET_FILE.exists():
        BUDGET_FILE.unlink()
    yield
    if BUDGET_FILE.exists():
        BUDGET_FILE.unlink()

SAMPLE_MARKET = MarketData(
    condition_id="0xabc", question="Will X happen?",
    yes_price=0.60, no_price=0.40,
    yes_token_id="t1", no_token_id="t2",
    volume_24h=100000, liquidity=20000, slug="will-x-happen",
)


def _mock_claude_response(prob: float, confidence: str = "B-"):
    resp = MagicMock()
    resp.content = [MagicMock()]
    resp.content[0].text = json.dumps({
        "probability": prob, "confidence": confidence,
        "reasoning_pro": "test reasoning pro",
        "reasoning_con": "test reasoning con",
        "key_evidence_for": ["a"], "key_evidence_against": ["b"],
    })
    resp.usage = MagicMock()
    resp.usage.input_tokens = 500
    resp.usage.output_tokens = 200
    return resp


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_unified_prompt_analysis(mock_cls):
    """Single unified call (replaced old dual-prompt)."""
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.70, "A"),
    ]
    analyst = AIAnalyst(AIConfig())
    result = analyst.analyze_market(SAMPLE_MARKET)
    assert result.ai_probability == pytest.approx(0.70)
    assert result.confidence in ("C", "B-", "B+", "A")


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_batch_analysis(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.65),
        _mock_claude_response(0.80),
    ]
    analyst = AIAnalyst(AIConfig(batch_size=5))
    results = analyst.analyze_batch([SAMPLE_MARKET, SAMPLE_MARKET])
    assert len(results) == 2


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_budget_exhausted_returns_neutral(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    analyst = AIAnalyst(AIConfig(monthly_budget_usd=0.001))
    # Simulate having already spent the budget
    analyst._month_cost_usd = 0.01
    result = analyst.analyze_market(SAMPLE_MARKET)
    # Should return neutral 0.5 without calling API
    assert result.ai_probability == 0.5
    assert result.confidence == "C"
    assert "BUDGET_EXHAUSTED" in result.reasoning_pro
    client.messages.create.assert_not_called()


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_cost_tracking_accumulates(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.70),
    ]
    analyst = AIAnalyst(AIConfig(monthly_budget_usd=12.0))
    # Reset any disk-loaded spending so we measure only this call
    analyst._month_cost_usd = 0.0
    analyst._sprint_cost_usd = 0.0
    analyst.analyze_market(SAMPLE_MARKET)
    # 1 unified call: 500 input × $3/M + 200 output × $15/M = $0.0045
    assert analyst._month_cost_usd == pytest.approx(0.0045)
    assert analyst.budget_remaining_usd == pytest.approx(12.0 - 0.0045)
