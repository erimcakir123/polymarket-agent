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
    c_section = UNIFIED_SYSTEM[c_idx:c_idx + 200].lower()
    assert "no data" in c_section or "no source" in c_section or "insufficient data" in c_section


def test_confidence_prompt_a_requires_multiple_sources():
    """A grade must mention multiple sources or strong data."""
    from src.ai_analyst import UNIFIED_SYSTEM
    a_idx = UNIFIED_SYSTEM.find('"A"')
    assert a_idx != -1
    a_section = UNIFIED_SYSTEM[a_idx:a_idx + 300].lower()
    assert "source" in a_section or "data" in a_section
