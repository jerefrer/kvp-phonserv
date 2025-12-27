import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import assert_equal_phonetics

sanskritPlaceholdersCases = [
  [ "ཧཱུྃ་", "(?)" ],
  [ "སྔགས་ཀྱི་ཕྲེང་བ་བཻ་ཌཱུ་རྱ་ཞུན་མའི་མདངས་ཅན", "ngak kyi trengwa (?) zhünmé dang chen" ],
  [ "ནང་དུ་སྲོག་གི་སྙིང་པོ་ཧཱུྃ་ཡིག་མཐིང་ག་མར་མེ་ལྟར་འབར་བའི་མཐར་སྔགས་ཀྱི་ཕྲེང་བ་བཻཌཱུརྱ་ཞུན་མའི་མདངས་ཅན་གཡས་བསྐོར་དུ་འཁོད་པར་", "nang du sok gi nyingpo (?) yik tinga marmé tar barwé tar ngak kyi trengwa (?) zhünmé dang chen yé kor du khöpar" ],
]

@pytest.mark.parametrize("tibetan, expected", sanskritPlaceholdersCases, ids=[case[1] for case in sanskritPlaceholdersCases])
def test_sanskrit_placeholders(tibetan, expected):
    assert_equal_phonetics(tibetan, expected, mode="words", schema="kvp")