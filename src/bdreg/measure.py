"""Text measures of regulatory burden.

Volume: word and section counts.
Restrictiveness: counts of binding language, split into obligations and
prohibitions. Definitional uses of 'shall' ('shall mean', 'shall include')
are removed first so that definitions do not inflate the score.
Cross-references: citations to other laws by number and year.

The term lists are a starting point. They should be validated against a
hand-coded sample of provisions before any results are reported.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .scrape import ACT_NO_RE, bangla_digits_to_ascii, roman_to_int

# English lexicon, applied to lower-cased text. Order matters: each match is
# removed after counting, so 'shall not' is never also counted as 'shall'.
EN_DEFINITIONAL = (
    r"\bshall\s+(?:mean|means|include|includes|have\s+the\s+(?:same\s+)?meanings?"
    r"|be\s+deemed\s+to\s+(?:mean|include))\b"
)
EN_PROHIBITION = (
    r"\b(?:shall\s+not|must\s+not|may\s+not|no\s+person\s+shall"
    r"|(?:is|are)\s+prohibited|prohibited\s+from)\b"
)
EN_OBLIGATION = r"\b(?:shall|must|(?:is|are)\s+(?:required|bound|obliged)\s+to)\b"
EN_PERMISSION = r"\bmay\b"
EN_PENALTY = r"\b(?:punishable|imprisonment|fine\s+which\s+may\s+extend)\b"

# Bangla lexicon (preliminary). Laws enacted since 1987 are in Bangla.
BN_DEFINITIONAL = r"(?:অর্থ\s+[^।]{0,40}?বুঝাইবে)"
BN_PROHIBITION = r"(?:করা\s+যাইবে\s+না|করিতে\s+পারিবে\s+না|নিষিদ্ধ)"
BN_OBLIGATION = r"(?:করিতে\s+হইবে|করিবে|বাধ্য\s+থাকিবে|বাধ্যতামূলক)"
BN_PERMISSION = r"(?:করিতে\s+পারিবে)"
BN_PENALTY = r"(?:দণ্ডনীয়|কারাদণ্ড|অর্থদণ্ড)"

WORD_RE = re.compile(r"[A-Za-z\u0980-\u09FF]+(?:'[A-Za-z]+)?")
SECTION_RE = re.compile(r"(?m)^\s*([0-9০-৯]+[A-Z]?)\.\s")


@dataclass
class Measures:
    n_words: int
    n_sections: int
    obligations: int
    prohibitions: int
    permissions: int
    definitional: int
    penalties: int

    @property
    def binding(self) -> int:
        return self.obligations + self.prohibitions

    @property
    def binding_per_1000(self) -> float:
        return 1000 * self.binding / self.n_words if self.n_words else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["binding"] = self.binding
        d["binding_per_1000"] = round(self.binding_per_1000, 3)
        return d


def _count_and_strip(pattern: str, text: str) -> tuple[int, str]:
    rx = re.compile(pattern, re.IGNORECASE)
    return len(rx.findall(text)), rx.sub(" ", text)


def measure(text: str, language: str = "en") -> Measures:
    n_words = len(WORD_RE.findall(text))
    n_sections = len(SECTION_RE.findall(text))
    t = text.lower()
    if language == "bn":
        lex = (BN_DEFINITIONAL, BN_PROHIBITION, BN_PENALTY, BN_OBLIGATION, BN_PERMISSION)
    else:
        lex = (EN_DEFINITIONAL, EN_PROHIBITION, EN_PENALTY, EN_OBLIGATION, EN_PERMISSION)
    definitional, t = _count_and_strip(lex[0], t)
    prohibitions, t = _count_and_strip(lex[1], t)
    penalties, t = _count_and_strip(lex[2], t)
    if language == "bn":
        permissions, t = _count_and_strip(lex[4], t)  # 'করিতে পারিবে' before 'করিবে'
        obligations, t = _count_and_strip(lex[3], t)
    else:
        obligations, t = _count_and_strip(lex[3], t)
        permissions = len(re.findall(lex[4], t))
    return Measures(n_words, n_sections, obligations, prohibitions, permissions, definitional, penalties)


def cross_references(text: str) -> list[tuple[str, int]]:
    """Return the (act number, year) pairs cited in a text, e.g. ('45', 1860)."""
    t = bangla_digits_to_ascii(text)
    return [(str(roman_to_int(n)), int(y)) for n, y in ACT_NO_RE.findall(t)]
