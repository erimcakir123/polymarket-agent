"""Kayıp-tarafı (loss-cut) çıkışları market modunda satar; kâr/near-resolve satmaz."""
from src.models.enums import ExitReason
from src.orchestration.exit_processor import _is_loss_cut


def test_loss_cut_reasons_true():
    for r in (ExitReason.STOP_LOSS, ExitReason.GRADUATED_SL, ExitReason.PARTIAL_SL,
              ExitReason.NEVER_IN_PROFIT, ExitReason.ULTRA_LOW_GUARD, ExitReason.HOLD_REVOKED):
        assert _is_loss_cut(r) is True


def test_non_loss_cut_reasons_false():
    for r in (ExitReason.NEAR_RESOLVE, ExitReason.SCALE_OUT):
        assert _is_loss_cut(r) is False
