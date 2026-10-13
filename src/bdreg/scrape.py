"""Polite scraper for the Laws of Bangladesh portal (bdlaws.minlaw.gov.bd).

The portal publishes the consolidated text of laws in force. Each law has an
index page (act-<id>.html) and a full-text page (act-details-<id>.html).

The URL patterns and HTML selectors below reflect the site layout at the time
of writing. Check them on a first run; websites change.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://bdlaws.minlaw.gov.bd"
INDEX_PATH = "/laws-of-bangladesh-chronological-index.html"
ACT_LINK_RE = re.compile(r"act-(\d+)\.html$")
DETAILS_PATH = "/act-details-{act_id}.html"

# Candidate containers for the law text, tried in order.
TEXT_SELECTORS = ["div.lineremoves", "div.txt-details", "div.law-content", "div.col-md-12"]

USER_AGENT = "bd-regulation-index research scraper (contact: alimranbd@gmail.com)"

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
TITLE_YEAR_RE = re.compile(r",\s*(\d{4})\b")
ACT_NO_RE = re.compile(
    r"\b(?:ACT|ORDINANCE|ORDER|REGULATION)\s*(?:NO\.?)?\s*([IVXLCDM]+|\d+)\s+OF\s+(\d{4})",
    re.IGNORECASE,
)
BANGLA_CHARS_RE = re.compile(r"[\u0980-\u09FF]")


@dataclass
class Act:
    act_id: int
    title: str
    year: int | None
    act_number: str | None
    language: str
    url: str
    text: str


def roman_to_int(s: str) -> int:
    """Convert a Roman numeral such as 'XLV' to 45. Digits pass through."""
    if s.isdigit():
        return int(s)
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        val = ROMAN[ch]
        total += -val if val < prev else val
        prev = max(prev, val)
    return total


def bangla_digits_to_ascii(s: str) -> str:
    return s.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))


def parse_title(title: str) -> tuple[int | None, str | None]:
    """Return (year, act number) from a title like 'The Penal Code, 1860 ( ACT NO. XLV OF 1860 )'."""
    t = bangla_digits_to_ascii(title)
    m = ACT_NO_RE.search(t)
    if m:
        return int(m.group(2)), str(roman_to_int(m.group(1)))
    m = TITLE_YEAR_RE.search(t)
    return (int(m.group(1)), None) if m else (None, None)


def detect_language(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown"
    share = sum(bool(BANGLA_CHARS_RE.match(c)) for c in letters) / len(letters)
    return "bn" if share > 0.5 else "en"


def extract_text(html: str) -> tuple[str, str]:
    """Return (title, body text) from a full-text page."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    h = soup.find(["h1", "h3"]) or soup.find("title")
    title = h.get_text(" ", strip=True) if h else ""
    for sel in TEXT_SELECTORS:
        nodes = soup.select(sel)
        if nodes:
            text = "\n".join(n.get_text("\n", strip=True) for n in nodes)
            break
    else:
        text = soup.get_text("\n", strip=True)
    return title, re.sub(r"[ \t]+", " ", text).strip()


def parse_index(html: str) -> list[int]:
    """Return the act ids linked from the chronological index, in order and without duplicates."""
    soup = BeautifulSoup(html, "html.parser")
    ids, seen = [], set()
    for a in soup.find_all("a", href=True):
        m = ACT_LINK_RE.search(a["href"])
        if m and (i := int(m.group(1))) not in seen:
            seen.add(i)
            ids.append(i)
    return ids


class Scraper:
    """Fetches pages with a delay and an on-disk cache, so reruns never hit the site twice."""

    def __init__(self, cache_dir: str | Path = "data/cache", delay: float = 1.5, base_url: str = BASE_URL):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def get(self, path: str) -> str:
        fname = self.cache / (path.strip("/").replace("/", "_") or "index.html")
        if fname.exists():
            return fname.read_text(encoding="utf-8")
        resp = self.session.get(self.base_url + path, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        fname.write_text(resp.text, encoding="utf-8")
        time.sleep(self.delay)
        return resp.text

    def act_ids(self) -> list[int]:
        return parse_index(self.get(INDEX_PATH))

    def fetch_act(self, act_id: int) -> Act:
        path = DETAILS_PATH.format(act_id=act_id)
        title, text = extract_text(self.get(path))
        year, number = parse_title(title)
        return Act(act_id, title, year, number, detect_language(text), self.base_url + path, text)
