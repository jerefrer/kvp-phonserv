import re
import inspect
from phonetics import segmentbywords, segmentbyone, segmentbytwo, add_phono

def assert_equal_phonetics(tibetan, expected, mode="words", schema="kvp", sanskrit_mode='phonetics'):
    clean_tibetan = clean_text(tibetan)
    clean_expected = clean_text(expected)
    phonetics = clean_text(phonetics_for(mode, schema, clean_tibetan, sanskrit_mode=sanskrit_mode))
    assert phonetics == clean_expected, f"Tibetan: {clean_tibetan} | Expected: {clean_expected} | Got: {phonetics}"

def phonetics_for(mode, schema, text, sanskrit_mode='phonetics'):
    res = {}
    match mode:
        case "words":
            add_phono(segmentbywords(text), res, sanskrit_mode=sanskrit_mode)
        case "one":
            add_phono(segmentbyone(text), res, sanskrit_mode=sanskrit_mode)
        case "two":
            add_phono(segmentbytwo(text), res, sanskrit_mode=sanskrit_mode)
    return res[schema.lower()]

def clean_text(text):
    return re.sub(r"\s+$", "", inspect.cleandoc(text), flags=re.MULTILINE)
