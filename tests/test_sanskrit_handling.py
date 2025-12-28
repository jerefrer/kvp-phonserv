import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import assert_equal_phonetics

# Test cases for Sanskrit handling with different modes
# Format: [tibetan, expected_keep, expected_iast, expected_phonetics]
# Note: "keep" mode uses the replacement map to detect Sanskrit and outputs (?)
# for all recognized Sanskrit patterns. Consecutive (?) markers are merged.
# IAST mode preserves diacritics (ā, ū, ṃ, etc.)
# Phonetics mode normalizes diacritics (ā→a, ū→u, ṃ→m, etc.)
sanskrit_cases = [
    # Pure Sanskrit mantra - all Sanskrit syllables get (?) in keep mode, merged
    ["ཨོཾ་ཨཱཿཧཱུྃ་", "(?)", "oṃ āḥ hūṃ", "om ah hung"],
    # Mixed Tibetan and Sanskrit
    ["རྡོ་རྗེ་སློབ་དཔོན་ཨོཾ་ཨཱཿཧཱུྃ་སངས་རྒྱས་དཔལ", "dorjé lopön (?) sangyé pal", "dorjé lopön oṃ āḥ hūṃ sangyé pal", "dorjé lopön om ah hung sangyé pal"],
    # Sanskrit words - all get (?) in keep mode
    ["མ་ཧཱ་", "(?)", "mahā", "maha"],
    ["དྷཱུ་ཏི", "(?)", "dhūti", "dhuti"],
    ["བྷནྡྷ", "(?)", "bhandha", "bhandha"],
]

@pytest.mark.parametrize("tibetan, expected_keep, expected_iast, expected_phonetics", sanskrit_cases)
def test_sanskrit_keep_mode(tibetan, expected_keep, expected_iast, expected_phonetics):
    """Test Sanskrit handling when sanskrit_mode='keep' (bophono default behavior)"""
    assert_equal_phonetics(tibetan, expected_keep, mode="words", schema="kvp", sanskrit_mode='keep')

@pytest.mark.parametrize("tibetan, expected_keep, expected_iast, expected_phonetics", sanskrit_cases)
def test_sanskrit_iast_mode(tibetan, expected_keep, expected_iast, expected_phonetics):
    """Test that Sanskrit is converted to IAST when sanskrit_mode='iast'"""
    assert_equal_phonetics(tibetan, expected_iast, mode="words", schema="kvp", sanskrit_mode='iast')

@pytest.mark.parametrize("tibetan, expected_keep, expected_iast, expected_phonetics", sanskrit_cases)
def test_sanskrit_phonetics_mode(tibetan, expected_keep, expected_iast, expected_phonetics):
    """Test that Sanskrit is converted to phonetics when sanskrit_mode='phonetics'"""
    assert_equal_phonetics(tibetan, expected_phonetics, mode="words", schema="kvp", sanskrit_mode='phonetics')

# Test anusvara style options
anusvara_cases = [
    ["ཨོཾ་", "oṃ", "oṁ"],
]

@pytest.mark.parametrize("tibetan, expected_m_under, expected_m_over", anusvara_cases)
def test_anusvara_style(tibetan, expected_m_under, expected_m_over):
    """Test anusvara style options (ṃ vs ṁ)"""
    from phonetics import add_phono, segmentbywords
    
    # Test with ṃ (default)
    res = {}
    add_phono(segmentbywords(tibetan), res, sanskrit_mode='iast', anusvara_style='ṃ')
    assert expected_m_under in res['kvp'], f"Expected {expected_m_under} with ṃ style, got {res['kvp']}"
    
    # Test with ṁ
    res = {}
    add_phono(segmentbywords(tibetan), res, sanskrit_mode='iast', anusvara_style='ṁ')
    assert expected_m_over in res['kvp'], f"Expected {expected_m_over} with ṁ style, got {res['kvp']}"
