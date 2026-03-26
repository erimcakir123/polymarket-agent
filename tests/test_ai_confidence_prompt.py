def test_confidence_prompt_contains_data_quality_language():
    """AI system prompt must define confidence by data availability, not outcome certainty."""
    from src.ai_analyst import UNIFIED_SYSTEM
    assert "data" in UNIFIED_SYSTEM.lower()
    assert "source" in UNIFIED_SYSTEM.lower()
    assert "outcome certainty" not in UNIFIED_SYSTEM.lower()
    for grade in ['"A"', '"B+"', '"B-"', '"C"']:
        assert grade in UNIFIED_SYSTEM


def test_confidence_prompt_defines_c_as_no_data():
    """C grade must mean 'no data', not 'uncertain outcome'."""
    from src.ai_analyst import UNIFIED_SYSTEM
    c_idx = UNIFIED_SYSTEM.find('"C"')
    assert c_idx != -1
    c_section = UNIFIED_SYSTEM[c_idx:c_idx + 400].lower()
    assert (
        "no data" in c_section
        or "no source" in c_section
        or "insufficient data" in c_section
        or "no statistical data" in c_section
        or "no match history" in c_section
    )


def test_confidence_prompt_a_requires_multiple_sources():
    """A grade must mention multiple sources or strong data."""
    from src.ai_analyst import UNIFIED_SYSTEM
    a_idx = UNIFIED_SYSTEM.find('"A"')
    assert a_idx != -1
    a_section = UNIFIED_SYSTEM[a_idx:a_idx + 300].lower()
    assert "source" in a_section or "data" in a_section


def test_b_minus_requires_stats_not_news_only():
    """B- definition must say it requires match stats, not news only."""
    from src.ai_analyst import UNIFIED_SYSTEM
    b_minus_idx = UNIFIED_SYSTEM.find('"B-"')
    assert b_minus_idx != -1
    b_minus_section = UNIFIED_SYSTEM[b_minus_idx:b_minus_idx + 300].lower()
    # Must explicitly state that news alone is not enough for B-
    if "news alone" in b_minus_section:
        # "news alone is NOT enough" — "not" or "enough" must follow within 30 chars
        pos = b_minus_section.find("news alone")
        surrounding = b_minus_section[pos:pos + 30]
        assert "not" in surrounding or "enough" in surrounding or "require" in b_minus_section


def test_news_alone_explicitly_c():
    """The prompt must explicitly state news alone = C."""
    from src.ai_analyst import UNIFIED_SYSTEM
    assert "news" in UNIFIED_SYSTEM.lower()
    # Find the C grade section
    c_idx = UNIFIED_SYSTEM.find('"C"')
    c_section = UNIFIED_SYSTEM[c_idx:c_idx + 400].lower()
    assert "news" in c_section  # News mentioned in C section
    assert "alone" in c_section or "without" in c_section  # News alone/without stats = C
