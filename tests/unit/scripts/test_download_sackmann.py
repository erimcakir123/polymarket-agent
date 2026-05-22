"""Download Sackmann CSV script — smoke test."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from scripts.download_sackmann import (
    download_year,
    download_challenger_year,
    SACKMANN_URL_TEMPLATE,
    SACKMANN_CHALLENGER_URL_TEMPLATE,
)


def test_download_url_format():
    url = SACKMANN_URL_TEMPLATE.format(year=2025)
    assert "JeffSackmann" in url
    assert "atp_matches_2025.csv" in url


def test_download_challenger_url_format():
    url = SACKMANN_CHALLENGER_URL_TEMPLATE.format(year=2025)
    assert "JeffSackmann" in url
    assert "atp_matches_qual_chall_2025.csv" in url


def test_download_year_writes_file(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "header1,header2\nval1,val2\n"
    with patch("scripts.download_sackmann.requests.get", return_value=mock_response):
        download_year(year=2025, target_dir=tmp_path)
    output = tmp_path / "atp_matches_2025.csv"
    assert output.exists()
    assert "val1" in output.read_text(encoding="utf-8")


def test_download_year_404_does_not_crash(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("scripts.download_sackmann.requests.get", return_value=mock_response):
        # Should log warning, not raise
        download_year(year=2099, target_dir=tmp_path)
    assert not (tmp_path / "atp_matches_2099.csv").exists()


def test_download_challenger_year_writes_file(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "header1,header2\nval1,val2\n"
    with patch("scripts.download_sackmann.requests.get", return_value=mock_response):
        download_challenger_year(year=2025, target_dir=tmp_path)
    output = tmp_path / "atp_matches_qual_chall_2025.csv"
    assert output.exists()
    assert "val1" in output.read_text(encoding="utf-8")


def test_download_challenger_year_404_does_not_crash(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("scripts.download_sackmann.requests.get", return_value=mock_response):
        download_challenger_year(year=2099, target_dir=tmp_path)
    assert not (tmp_path / "atp_matches_qual_chall_2099.csv").exists()
