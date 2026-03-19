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


def _mock_claude_response(prob: float, confidence: str = "medium"):
    resp = MagicMock()
    resp.content = [MagicMock()]
    resp.content[0].text = json.dumps({
        "probability": prob, "confidence": confidence,
        "reasoning": "test reasoning",
        "key_evidence_for": ["a"], "key_evidence_against": ["b"],
    })
    resp.usage = MagicMock()
    resp.usage.input_tokens = 500
    resp.usage.output_tokens = 200
    return resp


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_dual_prompt_averages(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.70, "high"),
        _mock_claude_response(0.60, "medium"),
    ]
    analyst = AIAnalyst(AIConfig())
    result = analyst.analyze_market(SAMPLE_MARKET)
    assert 0.60 <= result.ai_probability <= 0.70
    assert result.confidence in ("low", "medium", "high")


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_batch_analysis(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.65), _mock_claude_response(0.55),
        _mock_claude_response(0.80), _mock_claude_response(0.70),
    ]
    analyst = AIAnalyst(AIConfig(batch_size=5))
    results = analyst.analyze_batch([SAMPLE_MARKET, SAMPLE_MARKET])
    assert len(results) == 2


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_budget_exhausted_returns_market_price(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    analyst = AIAnalyst(AIConfig(monthly_budget_usd=0.001))
    # Simulate having already spent the budget
    analyst._month_cost_usd = 0.01
    result = analyst.analyze_market(SAMPLE_MARKET)
    # Should return market price without calling API
    assert result.ai_probability == SAMPLE_MARKET.yes_price
    assert result.confidence == "low"
    assert "Budget exhausted" in result.reasoning_pro
    client.messages.create.assert_not_called()


@patch.object(ai_analyst_mod.anthropic, "Anthropic")
def test_cost_tracking_accumulates(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.70), _mock_claude_response(0.60),
    ]
    analyst = AIAnalyst(AIConfig(monthly_budget_usd=12.0))
    analyst.analyze_market(SAMPLE_MARKET)
    # 2 calls × (500 input × $3/M + 200 output × $15/M) = 2 × $0.0045 = $0.009
    assert analyst._month_cost_usd == pytest.approx(0.009)
    assert analyst.budget_remaining_usd == pytest.approx(12.0 - 0.009)
