import pytest

from src.orchestration.live_confirmation import (
    confirm_live_if_needed,
    require_live_confirmation,
)


def test_confirm_live_if_needed_skips_when_not_live():
    # is_live=False → hiçbir onay istenmez, sessizce döner
    confirm_live_if_needed(is_live=False)


def test_tty_with_correct_phrase_passes():
    require_live_confirmation(is_tty=True, env_value=None, prompt_fn=lambda: "CONFIRM LIVE")


def test_tty_with_wrong_phrase_aborts():
    with pytest.raises(SystemExit):
        require_live_confirmation(is_tty=True, env_value=None, prompt_fn=lambda: "no")


def test_headless_with_env_flag_passes():
    require_live_confirmation(is_tty=False, env_value="1", prompt_fn=None)


def test_headless_without_env_flag_aborts():
    with pytest.raises(SystemExit):
        require_live_confirmation(is_tty=False, env_value=None, prompt_fn=None)
