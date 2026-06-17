from src.domain.control.trading_control import TradingControl


def test_default_not_paused():
    assert TradingControl().paused is False


def test_pause_then_resume():
    tc = TradingControl()
    tc.pause()
    assert tc.paused is True
    tc.resume()
    assert tc.paused is False


def test_roundtrip_serialization():
    tc = TradingControl()
    tc.pause()
    restored = TradingControl.from_dict(tc.to_dict())
    assert restored.paused is True


def test_from_dict_missing_key_defaults_false():
    assert TradingControl.from_dict({}).paused is False
