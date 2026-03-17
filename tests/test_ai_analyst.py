import json, pytest
from unittest.mock import patch, MagicMock
from src.models import MarketData

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
    return resp


@patch("src.ai_analyst.anthropic.Anthropic")
def test_dual_prompt_averages(mock_cls):
    from src.ai_analyst import AIAnalyst
    from src.config import AIConfig
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


@patch("src.ai_analyst.anthropic.Anthropic")
def test_batch_analysis(mock_cls):
    from src.ai_analyst import AIAnalyst
    from src.config import AIConfig
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.65), _mock_claude_response(0.55),
        _mock_claude_response(0.80), _mock_claude_response(0.70),
    ]
    analyst = AIAnalyst(AIConfig(batch_size=5))
    results = analyst.analyze_batch([SAMPLE_MARKET, SAMPLE_MARKET])
    assert len(results) == 2
