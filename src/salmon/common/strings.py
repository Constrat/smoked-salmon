import re
import unicodedata

from salmon.common.regexes import re_strip
from salmon.constants import GENRE_LIST
from salmon.errors import GenreNotInWhitelist

_ARTICLES = {"a", "an", "the"}
_COORDINATING_CONJUNCTIONS = {"and", "but", "or", "nor", "for", "yet", "so"}
_SHORT_PREPOSITIONS = {"as", "at", "by", "for", "in", "of", "on", "to", "from"}
_LOWERCASE_SPECIALS = {"vs.", "v.", "etc."}
_LOWERCASE_SPECIAL_PARTS = {"vs", "v", "etc"}
_BE_VERBS = {"be", "been", "being", "am", "are", "is", "was", "were", "ain't", "aint"}
_BUT_ADVERB_FOLLOWERS = {"a", "an", "few"}
_SEGMENT_START_PUNCT = "([\"'"
_SEGMENT_END_PUNCT = ")]\"'"
_MAJOR_BREAK_CHARS = {":", "?", "!", "-"}


def apply_mixed_case_title(text: str | None) -> str | None:
    """Apply standard mixed-case title capitalization rules to a string."""
    if not text:
        return text

    tokenized = re.split(r"(\s+)", text)
    words = []
    for i, token in enumerate(tokenized):
        if i % 2 == 1 or not token.strip():
            continue
        leading, core, trailing = _split_token(token)
        if not core or not re.search(r"[A-Za-z0-9]", core):
            continue
        words.append(
            {
                "token_index": i,
                "leading": leading,
                "core": core,
                "trailing": trailing,
            }
        )

    if not words:
        return text

    for pos, word in enumerate(words):
        prev_word = words[pos - 1] if pos > 0 else None
        next_word = words[pos + 1] if pos < len(words) - 1 else None

        is_segment_start = pos == 0 or _is_segment_start(word, prev_word)
        is_segment_end = pos == len(words) - 1 or _is_segment_end(word)
        force_capitalize = is_segment_start or is_segment_end

        lower_core = word["core"].lower()
        prev_core = prev_word["core"].lower() if prev_word else ""
        next_core = next_word["core"].lower() if next_word else ""

        # The adverbial "but" case ("You Are But a Draft") is title-cased.
        if (
            lower_core == "but"
            and not force_capitalize
            and prev_core in _BE_VERBS
            and (next_core in _BUT_ADVERB_FOLLOWERS or not next_core)
        ):
            formatted = "But"
        elif (
            lower_core in {"n", "o"}
            and not force_capitalize
            and ("'" in word["leading"] or "'" in word["trailing"])
        ):
            formatted = lower_core
        else:
            formatted = _format_core(word["core"], force_capitalize)

        tokenized[word["token_index"]] = f"{word['leading']}{formatted}{word['trailing']}"

    return "".join(tokenized)


def _split_token(token: str) -> tuple[str, str, str]:
    match = re.match(r"^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$", token)
    if not match:
        return "", token, ""
    return match.group(1), match.group(2), match.group(3)


def _is_segment_start(word: dict[str, str], prev_word: dict[str, str] | None) -> bool:
    if word["leading"] and any(c in _SEGMENT_START_PUNCT for c in word["leading"]):
        return True
    if not prev_word:
        return True
    prev_trailing = prev_word["trailing"]
    return any(c in _MAJOR_BREAK_CHARS for c in prev_trailing) or any(c in _SEGMENT_START_PUNCT for c in prev_trailing)


def _is_segment_end(word: dict[str, str]) -> bool:
    trailing = word["trailing"]
    if not trailing:
        return False
    return any(c in _MAJOR_BREAK_CHARS for c in trailing) or any(c in _SEGMENT_END_PUNCT for c in trailing)


def _format_core(core: str, force_capitalize: bool) -> str:
    if _is_acronym(core):
        return core
    if core.lower() in _LOWERCASE_SPECIALS and not force_capitalize:
        return core.lower()

    parts = re.split(r"(-)", core)
    formatted_parts = []
    for part in parts:
        if part == "-":
            formatted_parts.append(part)
            continue
        formatted_parts.append(_format_part(part, force_capitalize))
    return "".join(formatted_parts)


def _format_part(part: str, force_capitalize: bool) -> str:
    if _is_acronym(part):
        return part

    lower = part.lower()
    if lower in _LOWERCASE_SPECIAL_PARTS and not force_capitalize:
        return lower
    lowercase_words = _ARTICLES | _COORDINATING_CONJUNCTIONS | _SHORT_PREPOSITIONS
    if lower in lowercase_words and not force_capitalize:
        return lower

    return _capitalize_first_alpha(part)


def _is_acronym(token: str) -> bool:
    if len(token) <= 1:
        return False
    if token.isupper() and re.search(r"[A-Z]", token):
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", token):
        return True
    return False


def _capitalize_first_alpha(value: str) -> str:
    chars = list(value.lower())
    for i, ch in enumerate(chars):
        if ch.isalpha():
            chars[i] = ch.upper()
            break
    return "".join(chars)


def make_searchstrs(artists, album, normalize=False) -> list[str]:
    """Generate search strings from artists and album name.

    Args:
        artists: List of (artist_name, importance) tuples.
        album: Album name.
        normalize: Whether to normalize accents.

    Returns:
        List of search strings.
    """
    main_artists = [a for a, i in artists if i == "main"]
    album = album or ""
    album = re.sub(r" ?(- )? (EP|Single)", "", album)
    album = re.sub(r"\(?[Ff]eat(\.|uring)? [^\)]+\)?", "", album)

    search: str | list[str]
    if len(main_artists) > 3 or (main_artists and any("Various" in a for a in main_artists)) or len(main_artists) == 0:
        search = re_strip(album, filter_nonscrape=False)
    elif len(main_artists) == 1:
        search = re_strip(main_artists[0], album, filter_nonscrape=False)
    else:
        # 2 or 3 main artists
        search_list = [re_strip(art, album, filter_nonscrape=False) for art in main_artists]
        if normalize:
            result = normalize_accents(*search_list)
            return result if isinstance(result, list) else [result]
        return search_list

    if normalize:
        result = normalize_accents(search)
        return [result] if isinstance(result, str) else result
    return [search] if isinstance(search, str) else search


def normalize_accents(*strs: str) -> str | list[str]:
    """Normalize accents in strings using NFKD form.

    Args:
        *strs: Variable number of strings to normalize.

    Returns:
        Single normalized string if one input, list if multiple, empty string if none.
    """
    normalized = ["".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)) for s in strs]
    if not normalized:
        return ""
    return normalized if len(normalized) > 1 else normalized[0]


def less_uppers(one, two):
    """Return the string with less uppercase letters."""
    one_count = sum(1 for c in one if c.islower())
    two_count = sum(1 for c in two if c.islower())
    return one if one_count >= two_count else two


def strip_template_keys(template, key):
    """Strip all unused brackets from the folder name."""
    folder = re.sub(r" *[\[{\(]*{" + key + r"}[\]}\)]* *", " ", template).strip()
    return re.sub(r" *- *$", "", folder)


def fetch_genre(genre: str) -> set[str]:
    """Fetch standardized genre from whitelist.

    Args:
        genre: The genre string to look up.

    Returns:
        Set of standardized genre strings.

    Raises:
        GenreNotInWhitelist: If genre is not in whitelist.
    """
    normalized = normalize_accents(genre)
    if isinstance(normalized, list):
        normalized = normalized[0] if normalized else ""
    key_search = re.sub(r"[^a-z]", "", normalized.lower().replace("&", "and"))
    try:
        return GENRE_LIST[key_search]
    except KeyError:
        raise GenreNotInWhitelist from None


def truncate(string, length):
    if len(string) < length:
        return string
    return f"{string[: length - 3]}..."
