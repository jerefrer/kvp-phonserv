import re
import unicodedata
from botok import Text, WordTokenizer
import bophono
import csv
import os

try:
    from tibetan_sanskrit_transliteration_data import load_replacements
    _SANSKRIT_REPLACEMENTS = load_replacements()
except ImportError:
    _SANSKRIT_REPLACEMENTS = []

def _normalize_tibetan(text):
    """
    Normalize Tibetan text (ported from tibetan-normalizer JS).
    """
    # Normalize Unicode
    normalized = unicodedata.normalize('NFC', text)
    
    # Normalize combined letters
    normalized = normalized.replace(' ', ' ')  # Non-breaking space
    normalized = normalized.replace('ༀ', 'ཨོཾ')  # Om symbol
    normalized = normalized.replace('ཀྵ', 'ཀྵ')
    normalized = normalized.replace('བྷ', 'བྷ')
    normalized = re.sub(r'ི+', 'ི', normalized)  # Multiple i vowels
    normalized = re.sub(r'ུ+', 'ུ', normalized)  # Multiple u vowels
    normalized = normalized.replace('ཱུ', 'ཱུ')
    normalized = normalized.replace('ཱི', 'ཱི')
    normalized = normalized.replace('ཱྀ', 'ཱྀ')
    normalized = normalized.replace('དྷ', 'དྷ')
    normalized = normalized.replace('གྷ', 'གྷ')
    normalized = normalized.replace('ཪླ', 'རླ')
    normalized = normalized.replace('ྡྷ', 'ྡྷ')
    
    # Normalize tsheks
    # Malformed: anusvara before vowel - swap them
    normalized = re.sub(r'(ཾ)([ཱེིོྀུ])', r'\2\1', normalized)
    normalized = normalized.replace('༌', '་')  # Alternative tshek
    normalized = re.sub(r'་+', '་', normalized)  # Multiple consecutive tsheks
    
    return normalized

def _normalize_iast_to_phonetics(text):
    """
    Normalize IAST text by removing diacritics for phonetic output.
    """
    replacements = [
        ('ā', 'a'), ('ī', 'i'), ('ū', 'u'),
        ('ṛ', 'ri'), ('ṝ', 'ri'), ('ḷ', 'li'), ('ḹ', 'li'),
        ('ṃ', 'm'), ('ṁ', 'm'), ('ḥ', 'h'),
        ('ṅ', 'ng'), ('ñ', 'ny'),
        ('ṭ', 't'), ('ḍ', 'd'), ('ṇ', 'n'),
        ('ś', 'sh'), ('ṣ', 'sh'),
        ('é', 'e'), ('ē', 'e'),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result

options_fastidious = {
    'weakAspirationChar': '3',
    'aspirateLowTones': True,
    'prefixStrategy': 'always',
    'aiAffixchar': 'ː',
    #'hightonechar':'̄',
    #'lowtonechar':'̱',
    'nasalchar': '',
    'stopSDMode': "eow",
    'eatP': False,
    'useUnreleasedStops': True,
    'eatK': False,
    'syllablesepchar': ''
}

WT = WordTokenizer()

# Default converters with (?) markers for unknown syllables
PHON_KVP = bophono.UnicodeToApi(schema="KVP", options = {'unknownSyllableMarker': True})
PHON_API = bophono.UnicodeToApi(schema="MST", options = options_fastidious)

# Sanskrit-specific characters that don't appear in regular Tibetan words:
# - ཱ (0F71) vowel length mark (used in Sanskrit for long vowels like ā, ī, ū)
# - ཿ (0F7F) visarga (used in Sanskrit mantras like āḥ)
# - ཾ (0F7E) anusvara (bindu) - used in Sanskrit mantras like oṃ
# - ྃ (0F83) anusvara alternate form
# - ཥ (0F65) retroflex sha
# - ཊ (0F4A) retroflex ta
# - ཋ (0F4B) retroflex tha
# - ཌ (0F4C) retroflex da
# - ཎ (0F4E) retroflex na
# - ྀ (0F80) vocalic r
# - ྵ (0FB5) subjoined retroflex sha
# - ྷ (0FB7) subjoined ha (for aspirated voiced consonants like bha, dha, gha)
# - ྸ (0FB8) subjoined a (rare)
# Also match Sanskrit-specific consonant clusters:
# - ཀྟ (ka + subjoined ta) - common in Sanskrit (rakta, etc.)
# - བཛྲ (vajra) - specific Sanskrit word pattern
# - ཀྵ (kṣa) - common Sanskrit cluster
# - ཏྟ (ta + subjoined ta) - common in Sanskrit (citta, etc.)
_SANSKRIT_ONLY_CHARS = re.compile(r'[ཱཿཾྃཥཊཋཌཎྀྵྷྸ]|ཀྟ|གྟ|དྟ|པྟ|སྟ(?!ོ)|ནྟ|ཏྟ|ཀྵ|བཛྲ|ཛྲ')

def _is_sanskrit_specific(tibetan_pattern):
    """
    Check if a pattern contains Sanskrit-specific characters or combinations.
    This filters out patterns that would match regular Tibetan words.
    """
    return bool(_SANSKRIT_ONLY_CHARS.search(tibetan_pattern))

# Build compiled regex patterns for Sanskrit detection (sorted by length, longest first)
def _build_sanskrit_patterns():
    """Build sorted list of (compiled_regex, transliteration, phonetics) tuples."""
    if not _SANSKRIT_REPLACEMENTS:
        return []
    patterns = []
    for entry in _SANSKRIT_REPLACEMENTS:
        tibetan = entry.get('tibetan', '')
        transliteration = entry.get('transliteration', '')
        # If phonetics field is empty, normalize IAST to get phonetics
        phonetics = entry.get('phonetics', '')
        if not phonetics:
            phonetics = _normalize_iast_to_phonetics(transliteration)
        if tibetan and transliteration and _is_sanskrit_specific(tibetan):
            try:
                # Compile the pattern (some entries use regex)
                compiled = re.compile(tibetan)
                patterns.append((compiled, tibetan, transliteration, phonetics))
            except re.error:
                # If it's not a valid regex, escape it
                compiled = re.compile(re.escape(tibetan))
                patterns.append((compiled, tibetan, transliteration, phonetics))
    # Sort by pattern length (longest first) to match longer patterns before shorter ones
    patterns.sort(key=lambda x: len(x[1]), reverse=True)
    return patterns

_SANSKRIT_PATTERNS = _build_sanskrit_patterns()

def _find_sanskrit_matches(text):
    """
    Find all Sanskrit pattern matches in text.
    Returns list of (start, end, transliteration, phonetics) tuples, sorted by position.
    """
    if not _SANSKRIT_PATTERNS:
        return []
    
    matches = []
    for compiled_pattern, _, transliteration, phonetics in _SANSKRIT_PATTERNS:
        for match in compiled_pattern.finditer(text):
            matches.append((match.start(), match.end(), transliteration, phonetics))
    
    # Sort by start position, then by length (longer matches first for same start)
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    
    # Remove overlapping matches (keep the first/longest one)
    filtered = []
    last_end = 0
    for start, end, trans, phon in matches:
        if start >= last_end:
            filtered.append((start, end, trans, phon))
            last_end = end
    
    return filtered

def _process_word_sanskrit(word, sanskrit_mode, anusvara_style='ṃ'):
    """
    Process a single word, extracting Sanskrit parts and Tibetan parts.
    Returns list of (text, is_sanskrit) tuples.
    """
    if not _SANSKRIT_PATTERNS:
        return [(word, False)]
    
    matches = _find_sanskrit_matches(word)
    if not matches:
        return [(word, False)]
    
    result = []
    last_end = 0
    
    for start, end, transliteration, phonetics in matches:
        # Add any Tibetan text before this match
        if start > last_end:
            tibetan_part = word[last_end:start]
            if tibetan_part:
                result.append((tibetan_part, False))
        
        # Determine Sanskrit output based on mode
        if sanskrit_mode == 'iast':
            output = transliteration
            if anusvara_style == 'ṁ':
                output = output.replace('ṃ', 'ṁ')
        elif sanskrit_mode == 'phonetics':
            output = phonetics
        else:
            output = '(?)'
        
        result.append((output, True))
        last_end = end
    
    # Add any remaining Tibetan text after the last match
    if last_end < len(word):
        tibetan_part = word[last_end:]
        if tibetan_part:
            result.append((tibetan_part, False))
    
    return result

def segmentbyone(in_str):
    lines = _enforce_tshegs_at_the_end(in_str).split("\n")
    res = ""
    for l in lines:
        l = re.sub(r"([\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+[^\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]*)", r"\1 ", l)
        res += l+"\n"
    return res

def segmentbytwo(in_str):
    lines = _enforce_tshegs_at_the_end(in_str).split("\n")
    res = ""
    for l in lines:
        countsyls = len(re.findall("[\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+", l))
        l = re.sub(r"([\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+[^\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+[\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+[^\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]*)", r"\1 ", l)
        if countsyls % 2 == 1:
            l = re.sub(r" ([\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]+[^\u0F35\u0F37ཀ-\u0f7e\u0F80-\u0FBC]*)$", r"\1", l)
        res += l+"\n"
    return res

def segmentbywords(in_str):
    # Preserve newlines by processing line by line
    lines = in_str.splitlines()
    segmented_lines = []
    for line in lines:
        line = _enforce_tshegs_at_the_end(line)
        # Build a regex that matches any exception
        exception_patterns = sorted(_segmentation_exceptions.keys(), key=len, reverse=True)
        if not exception_patterns:
            # No exceptions, just use Botok as before
            segmented_lines.append(_segmentbywords_botok(line))
            continue
        pattern = "(" + "|".join(map(re.escape, exception_patterns)) + ")"
        # Split input into exceptions and non-exceptions
        parts = re.split(pattern, line)
        result = []
        i = 0
        while i < len(parts):
            part = parts[i]
            if part in _segmentation_exceptions:
                segmented_exception = _segmentation_exceptions[part]
                
                # Always add a space before the exception
                next_part = parts[i+1] if i+1 < len(parts) else ''
                next_part_stripped = next_part.lstrip()
                # Particles: འི, ར, ས
                if next_part_stripped.startswith(('འི', 'ར', 'ས')):
                    # No space after exception
                    result.append(f" {segmented_exception}")
                else:
                    combined = f"{segmented_exception}{next_part_stripped}"
                    processed_combined = _postsegment(combined)
                    # If there would have been a postsegment,
                    # Then don't add a space after the exception
                    # Otherwise add one
                    if processed_combined != combined:
                        result.append(f" {segmented_exception}")
                    else:
                        result.append(f" {segmented_exception} ")
            elif part.strip():
                result.append(_segmentbywords_botok(part))
            i += 1
        # Collapse multiple spaces to one, and strip leading/trailing space for each line
        segmented_lines.append(" ".join("".join(result).split()))
    return "\n".join(segmented_lines)


def _segmentbywords_botok(in_str):
    try:
        t = Text(in_str, tok_params={'profile': 'GMD'})
        tokens = t.custom_pipeline('dummy', _botok_tokenizer, _botok_modifier, 'dummy')
    except Exception as e:
        print(e)
        print("botok failed to segment "+in_str)
        return in_str
    res = ''
    first = True
    for token in tokens:
        if not first:
            res += " "
        first = False
        res += in_str[token['start']:token['end']]
    res = _presegment(res)
    res = _postsegment(res)
    return res

def _botok_tokenizer(in_str):
    return WT.tokenize(in_str)

def _botok_modifier(tokens):
    op = []
    for t in tokens:
        op_token = {
            'start': t.start,
            'end': t.start + t.len,
            'type': t.chunk_type
        }
        op.append(op_token)
    return op

# Splits MA prefix that should always be separate
def _presegment(in_str):
    in_str = re.sub(r"(^| )(མ)་", r" \2་ ", in_str)
    return in_str

def _postsegment(in_str):
    # Combine particle with previous syllable when there is just one
    in_str = re.sub(r"(^| )([^ ]+)[\u0F0B\u0F0C] +(མེད|བ|པ|བོ|ཝོ|མོ|བའི|བས|བའོ|པའི|པར|པས|པའོ|བོའི|བོར|བོས|བོའོ|པོའི|པོར|པོས|པོའོ|མའི|མས|མའོ|མོའི|མོར|མོའོ)($|[ ་-༔])", r"\1\2་\3\4", in_str)
    in_str = re.sub(r"([\u0F40-\u0FBC]) +([\u0F40-\u0FBC])", r"\1\2", in_str)
    # Make sure imperative endings are separate (chik, shok)
    in_str = re.sub(r"(གཅིག|ཅིག|ཞིག|ཤིགས|ཤིག|ཞོགས|ཤོགས|ཤོག|ཞོག)($|[ ་-༔])", r" \1\2", in_str)
    return in_str

def _load_segmentation_exceptions():
    exceptions = {}
    csv_path = os.path.join(os.path.dirname(__file__), "segmentation_exceptions.csv")
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                orig = row["ORIGINAL"].strip()
                seg = row["SEGMENTED"].strip()
                if orig and seg and not orig.startswith('#'):
                    exceptions[orig] = seg
    except Exception as e:
        print(f"Could not load segment exceptions: {e}")
    return exceptions

_segmentation_exceptions = _load_segmentation_exceptions()

def _enforce_tshegs_at_the_end(in_str):
    in_str = in_str.rstrip()
    if in_str and not re.search(r"[་།༎༔]$", in_str):
        in_str += "་"
    return in_str

def _clean_phono_output(phon_str):
    """Clean up phonetic output: merge consecutive (?) markers and trim spaces"""
    # Merge consecutive (?) markers (with optional spaces between), keep one trailing space
    phon_str = re.sub(r'\(\?\)(\s*\(\?\))+', '(?)', phon_str)
    # Collapse multiple spaces into one
    phon_str = re.sub(r'  +', ' ', phon_str)
    # Remove trailing space before newline or end
    phon_str = re.sub(r' +(\n|$)', r'\1', phon_str)
    return phon_str

def add_phono(in_str, res, sanskrit_mode=None, anusvara_style='ṃ'):
    """
    Add phonetic transcriptions to the result dictionary.
    
    Args:
        in_str: Input Tibetan text (segmented)
        res: Result dictionary to populate
        sanskrit_mode: None/'keep' for (?) markers, 'iast' for IAST, 'phonetics' for phonetic
        anusvara_style: 'ṃ' (default) or 'ṁ' for anusvara character
    """
    # Normalize Tibetan input first
    in_str = _normalize_tibetan(in_str)
    lines = in_str.split("\n")
    res_kvp = ""
    res_ipa = ""
    
    for l in lines:
        words = l.split()
        for word in words:
            # Process word to find Sanskrit patterns
            # Remove spaces but keep the word boundary
            matches = _find_sanskrit_matches(word)
            
            if not matches:
                # No Sanskrit - just phoneticize the whole word
                res_kvp += PHON_KVP.get_api(word) + ' '
                res_ipa += PHON_API.get_api(word) + ' '
                continue
            
            # Process parts of the word
            kvp_parts = []
            ipa_parts = []
            last_end = 0
            
            for start, end, transliteration, phonetics in matches:
                # Add any Tibetan text before this match
                if start > last_end:
                    tibetan_part = word[last_end:start]
                    if tibetan_part.strip('་'):
                        kvp_parts.append(PHON_KVP.get_api(tibetan_part))
                        ipa_parts.append(PHON_API.get_api(tibetan_part))
                
                # Determine Sanskrit output based on mode
                if sanskrit_mode == 'iast':
                    output = transliteration
                    if anusvara_style == 'ṁ':
                        output = output.replace('ṃ', 'ṁ')
                elif sanskrit_mode == 'phonetics':
                    output = phonetics
                else:
                    output = '(?)'
                
                kvp_parts.append(output)
                ipa_parts.append(output)
                last_end = end
            
            # Add any remaining Tibetan text after the last match
            if last_end < len(word):
                tibetan_part = word[last_end:]
                if tibetan_part.strip('་'):
                    kvp_parts.append(PHON_KVP.get_api(tibetan_part))
                    ipa_parts.append(PHON_API.get_api(tibetan_part))
            
            res_kvp += ' '.join(kvp_parts) + ' '
            res_ipa += ' '.join(ipa_parts) + ' '
        
        res_kvp += "\n"
        res_ipa += "\n"
    
    res["kvp"] = _clean_phono_output(res_kvp)
    res["ipa"] = _clean_phono_output(res_ipa)