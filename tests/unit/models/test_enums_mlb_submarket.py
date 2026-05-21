from src.models.enums import EntryReason


def test_mlb_submarket_entry_reason_exists() -> None:
    assert EntryReason.MLB_SUBMARKET == "mlb_submarket"
    assert EntryReason.MLB_SUBMARKET.value == "mlb_submarket"


def test_mlb_submarket_in_enum_iteration() -> None:
    values = {r.value for r in EntryReason}
    assert "mlb_submarket" in values
