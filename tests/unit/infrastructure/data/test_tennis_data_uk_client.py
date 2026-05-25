from pathlib import Path

import pytest


def _make_xlsx(tmp_path: Path, name: str, headers: list, rows: list) -> Path:
    """Helper to create a minimal xlsx for testing."""
    pytest.importorskip("openpyxl")
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    out = tmp_path / name
    wb.save(out)
    return out


def test_tennis_data_uk_parser_reads_xlsx(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    headers = [
        "ATP", "Location", "Tournament", "Date", "Series", "Court", "Surface",
        "Round", "Best of", "Winner", "Loser", "WRank", "LRank",
        "B365W", "B365L", "PSW", "PSL",
    ]
    rows = [
        [1, "Sydney", "ATP Cup", "2024-01-05", "ATP250", "Outdoor", "Hard",
         "F", 3, "Djokovic N.", "Federer R.", 1, 5, 1.50, 2.50, 1.55, 2.40],
    ]
    xlsx_path = _make_xlsx(tmp_path, "atp_2024.xlsx", headers, rows)
    assert xlsx_path.exists()
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_year("atp", 2024)
    assert len(matches) == 1
    m = matches[0]
    assert m.winner_name == "Djokovic N."
    assert m.surface == "Hard"
    assert m.pinnacle_winner_odds == 1.55
    assert m.pinnacle_loser_odds == 2.40
    assert m.winner_rank == 1
    assert m.loser_rank == 5


def test_tennis_data_uk_missing_file_returns_empty(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_year("atp", 1999)
    assert matches == []


def test_tennis_data_uk_load_years_combines(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    headers = [
        "ATP", "Location", "Tournament", "Date", "Series", "Court", "Surface",
        "Round", "Best of", "Winner", "Loser", "WRank", "LRank",
        "B365W", "B365L", "PSW", "PSL",
    ]
    _make_xlsx(tmp_path, "atp_2023.xlsx", headers, [
        [1, "X", "Y", "2023-01-01", "A", "Out", "Hard", "F", 3,
         "W1", "L1", 10, 20, 1.5, 2.5, 1.5, 2.5],
    ])
    _make_xlsx(tmp_path, "atp_2024.xlsx", headers, [
        [1, "X", "Y", "2024-01-01", "A", "Out", "Hard", "F", 3,
         "W2", "L2", 10, 20, 1.5, 2.5, 1.5, 2.5],
    ])
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_years("atp", [2023, 2024])
    assert len(matches) == 2
    assert {m.winner_name for m in matches} == {"W1", "W2"}
