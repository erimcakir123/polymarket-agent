"""Gate'in tennis için Kelly sizing kullandığını kanıtla."""
from src.domain.analysis.probability import BookmakerProbability
from src.models.market import MarketData
from src.models.signal import Signal
from src.strategy.entry.gate import GateConfig, _compute_position_size


def _market(sport: str = "tennis", yes_price: float = 0.50, no_price: float = 0.50) -> MarketData:
    return MarketData(
        condition_id="0xa", question="Alice vs Bob", slug="x",
        yes_token_id="t1", no_token_id="t2",
        yes_price=yes_price, no_price=no_price,
        liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag=sport, sports_market_type="moneyline",
    )


def _signal(direction: str = "BUY_YES", confidence: str = "A") -> Signal:
    return Signal(
        condition_id="0xa", token_id="t1", direction=direction,
        size_usdc=0.0, entry_price=0.50, confidence=confidence,
        anchor_probability=0.60, entry_reason="normal",
        market_price=0.50, edge=0.10, bookmaker_prob=0.60,
    )


def _bm_prob(p: float = 0.60) -> BookmakerProbability:
    return BookmakerProbability(
        probability=p, confidence="A", bookmaker_prob=p,
        num_bookmakers=5.0, has_sharp=True,
    )


def test_tennis_uses_kelly():
    """Tennis + edge → Kelly bet_size hesabı."""
    cfg = GateConfig(kelly_enabled_tennis=True, kelly_multiplier=0.25, kelly_max_pct=0.05)
    m = _market(sport="tennis", yes_price=0.50)
    s = _signal(direction="BUY_YES")
    bm = _bm_prob(p=0.60)
    bankroll = 1000.0
    size = _compute_position_size(m, s, bm, cfg, bankroll)
    # Kelly fraction = (0.60-0.50)/(1-0.50) = 0.20
    # raw = 1000 * 0.20 * 0.25 = 50
    # cap = 1000 * 0.05 = 50
    # min(50, 50) = 50
    assert abs(size - 50.0) < 1e-6


def test_tennis_buy_no_uses_inverted_probability():
    cfg = GateConfig(kelly_enabled_tennis=True, kelly_multiplier=0.25, kelly_max_pct=0.05)
    m = _market(sport="tennis", yes_price=0.30, no_price=0.70)
    s = _signal(direction="BUY_NO")
    bm = _bm_prob(p=0.20)  # P(YES)=0.20 → P(NO)=0.80, buying NO at 0.70 → Kelly>0
    bankroll = 1000.0
    size = _compute_position_size(m, s, bm, cfg, bankroll)
    # Kelly = (0.80 - 0.70) / (1 - 0.70) = 0.333
    # raw = 1000 * 0.333 * 0.25 = 83.3 → cap 50 → 50
    assert abs(size - 50.0) < 1e-6


def test_non_tennis_uses_fixed_sizing():
    cfg = GateConfig()
    m = _market(sport="nba", yes_price=0.50)
    s = _signal(confidence="A")
    bm = _bm_prob(p=0.65)
    size = _compute_position_size(m, s, bm, cfg, 1000.0)
    # Fixed A: 50.0
    assert size == 50.0


def test_tennis_kelly_off_uses_fixed():
    cfg = GateConfig(kelly_enabled_tennis=False)
    m = _market(sport="tennis", yes_price=0.50)
    s = _signal(confidence="A")
    bm = _bm_prob(p=0.65)
    size = _compute_position_size(m, s, bm, cfg, 1000.0)
    assert size == 50.0  # fixed A


def test_tennis_no_edge_fallback_to_fixed():
    """Kelly 0 dönerse fixed-tier fallback."""
    cfg = GateConfig(kelly_enabled_tennis=True)
    m = _market(sport="tennis", yes_price=0.60)
    s = _signal(confidence="A")
    bm = _bm_prob(p=0.55)  # p < price → no edge → Kelly 0
    size = _compute_position_size(m, s, bm, cfg, 1000.0)
    # Fallback to fixed A (moneyline = non-bimodal = 50.0)
    assert size == 50.0
