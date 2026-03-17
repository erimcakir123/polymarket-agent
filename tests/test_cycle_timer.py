import pytest


def test_default_interval():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    assert timer.get_interval() == 30


def test_breaking_news_shortens():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    timer.signal_breaking_news()
    assert timer.get_interval() == 10


def test_near_stop_loss_shortens():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    timer.signal_near_stop_loss()
    assert timer.get_interval() == 15


def test_night_mode_extends():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig(night_hours=[0, 1, 2, 3, 4, 5, 6]))
    timer.signal_night_mode(current_hour=3)
    assert timer.get_interval() == 60
