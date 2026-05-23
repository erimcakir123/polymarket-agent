from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_tto_for_first_batter_is_1():
    # 0 önceki PA → TTO 1
    assert MlbSubmarketEngine._tto_for_pa(0) == 1


def test_tto_for_8th_batter_still_1():
    # 8 önceki PA → hâlâ TTO 1 (lineup dönmedi)
    assert MlbSubmarketEngine._tto_for_pa(8) == 1


def test_tto_for_9th_pa_becomes_2():
    # 9 önceki PA → leadoff TTO 2 (lineup tam döndü)
    assert MlbSubmarketEngine._tto_for_pa(9) == 2


def test_tto_for_17_pa_is_2():
    # 17 = (9*1 + 8) → hâlâ TTO 2
    assert MlbSubmarketEngine._tto_for_pa(17) == 2


def test_tto_for_18_pa_is_3():
    # 18 = (9*2) → TTO 3
    assert MlbSubmarketEngine._tto_for_pa(18) == 3


def test_tto_caps_at_4():
    # 27+ → TTO 4 (max)
    assert MlbSubmarketEngine._tto_for_pa(27) == 4
    assert MlbSubmarketEngine._tto_for_pa(50) == 4
    assert MlbSubmarketEngine._tto_for_pa(100) == 4
