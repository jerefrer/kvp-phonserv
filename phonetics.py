import re
from botok import Text, WordTokenizer
import bophono
import csv
import os

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
PHON_KVP = bophono.UnicodeToApi(schema="KVP", options = {'unknownSyllableMarker': True})
PHON_API = bophono.UnicodeToApi(schema="MST", options = options_fastidious)

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
    phon_str = re.sub(r'\(\?\)\s*(\(\?\)\s*)+', '(?) ', phon_str)
    # Collapse multiple spaces into one
    phon_str = re.sub(r'  +', ' ', phon_str)
    # Remove trailing space before newline or end
    phon_str = re.sub(r' +(\n|$)', r'\1', phon_str)
    return phon_str

def add_phono(in_str, res):
    lines = in_str.split("\n")
    res_kvp = ""
    res_ipa = ""
    for l in lines:
        words = l.split()
        for word in words:
            res_kvp += PHON_KVP.get_api(word)+' '
            res_ipa += PHON_API.get_api(word)+' '
        res_kvp += "\n"
        res_ipa += "\n"
    res["kvp"] = _clean_phono_output(res_kvp)
    res["ipa"] = _clean_phono_output(res_ipa)