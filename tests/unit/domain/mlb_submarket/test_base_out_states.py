import pytest
from src.domain.mlb_submarket.base_out_states import (
    INITIAL_STATE,
    INNING_ENDED,
    encode,
    decode,
)


def test_initial_state_is_zero() -> None:
    assert INITIAL_STATE == 0


def test_inning_ended_sentinel() -> None:
    assert INNING_ENDED == -1


def test_encode_decode_roundtrip() -> None:
    for outs in (0, 1, 2):
        for r1 in (False, True):
            for r2 in (False, True):
                for r3 in (False, True):
                    idx = encode(outs, (r1, r2, r3))
                    assert 0 <= idx <= 23
                    decoded = decode(idx)
                    assert decoded == (outs, (r1, r2, r3))


def test_encode_specific_states() -> None:
    assert encode(0, (False, False, False)) == 0    # nobody on, 0 out
    assert encode(0, (False, False, True)) == 4     # runner on 3B, 0 out
    assert encode(0, (True, True, True)) == 7       # bases loaded, 0 out
    assert encode(1, (False, False, False)) == 8    # 1 out, bases empty
    assert encode(2, (True, False, False)) == 17    # 2 out, runner on 1B


def test_decode_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        decode(24)
    with pytest.raises(ValueError):
        decode(-2)


def test_encode_invalid_outs_raises() -> None:
    with pytest.raises(ValueError):
        encode(3, (False, False, False))
    with pytest.raises(ValueError):
        encode(-1, (False, False, False))
