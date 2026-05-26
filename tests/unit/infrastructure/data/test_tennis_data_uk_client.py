from pathlib import Path


_CSV_HEADER = (
    "Date,Tournament,Surface,Round,Best of,Winner,Loser,WRank,LRank,"
    "B365W,B365L,PSW,PSL\n"
)


def _write_csv(tmp_path: Path, filename: str, rows: list[str]) -> Path:
    path = tmp_path / filename
    path.write_text(_CSV_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_load_year_filters_by_date_prefix(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient

    _write_csv(
        tmp_path, "df_atp.csv",
        [
            "2023-01-05,ATP Cup,Hard,F,3,Djokovic N.,Federer R.,1,5,1.5,2.5,1.55,2.40",
            "2024-01-05,ATP Cup,Hard,F,3,Sinner J.,Medvedev D.,2,4,1.8,2.0,1.85,1.95",
        ],
    )
    client = TennisDataUKClient(cache_dir=tmp_path)

    matches_2024 = client.load_year("atp", 2024)
    assert len(matches_2024) == 1
    m = matches_2024[0]
    assert m.winner_name == "Sinner J."
    assert m.surface == "Hard"
    assert m.pinnacle_winner_odds == 1.85
    assert m.pinnacle_loser_odds == 1.95
    assert m.winner_rank == 2
    assert m.loser_rank == 4


def test_load_all_returns_every_row(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient

    _write_csv(
        tmp_path, "df_atp.csv",
        [
            "2018-01-01,X,Hard,F,3,W1,L1,10,20,1.5,2.5,1.5,2.5",
            "2019-01-01,X,Hard,F,3,W2,L2,10,20,1.5,2.5,1.5,2.5",
            "2020-01-01,X,Hard,F,3,W3,L3,10,20,1.5,2.5,1.5,2.5",
        ],
    )
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_all("atp")
    assert {m.winner_name for m in matches} == {"W1", "W2", "W3"}


def test_load_years_combines_selected_years(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient

    _write_csv(
        tmp_path, "df_wta.csv",
        [
            "2018-01-01,X,Hard,F,3,W1,L1,10,20,1.5,2.5,1.5,2.5",
            "2019-01-01,X,Hard,F,3,W2,L2,10,20,1.5,2.5,1.5,2.5",
            "2020-01-01,X,Hard,F,3,W3,L3,10,20,1.5,2.5,1.5,2.5",
        ],
    )
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_years("wta", [2018, 2020])
    assert {m.winner_name for m in matches} == {"W1", "W3"}


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    client = TennisDataUKClient(cache_dir=tmp_path)
    assert client.load_year("atp", 1999) == []
    assert client.load_all("wta") == []


def test_unknown_tour_returns_empty(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    client = TennisDataUKClient(cache_dir=tmp_path)
    assert client.load_all("itf") == []


def test_missing_pinnacle_odds_become_none(tmp_path: Path) -> None:
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    _write_csv(
        tmp_path, "df_atp.csv",
        [
            "2000-01-03,X,Hard,F,3,Dosedel S.,Ljubicic I.,50,60,1.5,2.5,,",
        ],
    )
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_year("atp", 2000)
    assert len(matches) == 1
    assert matches[0].pinnacle_winner_odds is None
    assert matches[0].pinnacle_loser_odds is None
