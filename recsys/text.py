"""Токенизация и стемминг названий закупок и позиций."""
import re
from functools import lru_cache

import snowballstemmer

_stemmer = snowballstemmer.stemmer("russian")
_TOKEN = re.compile(r"[a-zа-я0-9]+")
_STOP = frozenset(
    "и в во на для по с со от из к не или а о об у при до за под над же ли бы то это как что "
    "шт ед".split()
)


@lru_cache(maxsize=None)
def _stem(token: str) -> str:
    return _stemmer.stemWord(token)


def analyze(text: str) -> list[str]:
    tokens = []
    for token in _TOKEN.findall(text.lower().replace("ё", "е")):
        if len(token) < 2 or token.isdigit() or token in _STOP:
            continue
        tokens.append(_stem(token))
    return tokens
