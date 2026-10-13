"""SQLite storage. One row per act, one row of measures per act, one row per citation."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS acts (
    act_id      INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    year        INTEGER,
    act_number  TEXT,
    language    TEXT,
    url         TEXT,
    text        TEXT,
    scraped_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS measures (
    act_id            INTEGER PRIMARY KEY REFERENCES acts(act_id),
    n_words           INTEGER,
    n_sections        INTEGER,
    obligations       INTEGER,
    prohibitions      INTEGER,
    permissions       INTEGER,
    definitional      INTEGER,
    penalties         INTEGER,
    binding           INTEGER,
    binding_per_1000  REAL
);
CREATE TABLE IF NOT EXISTS citations (
    src_act_id     INTEGER REFERENCES acts(act_id),
    target_number  TEXT,
    target_year    INTEGER,
    target_act_id  INTEGER REFERENCES acts(act_id)
);
CREATE INDEX IF NOT EXISTS idx_acts_num_year ON acts(act_number, year);
"""

# Volume and restrictiveness by year of enactment.
BY_YEAR_SQL = """
SELECT a.year,
       COUNT(*)                        AS n_acts,
       SUM(m.n_words)                  AS words,
       SUM(m.binding)                  AS binding,
       1000.0 * SUM(m.binding) / SUM(m.n_words) AS binding_per_1000
FROM acts a JOIN measures m USING (act_id)
WHERE a.year IS NOT NULL AND m.n_words > 0
GROUP BY a.year
ORDER BY a.year;
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def upsert_act(con, act) -> None:
    con.execute(
        "INSERT OR REPLACE INTO acts (act_id, title, year, act_number, language, url, text) VALUES (?,?,?,?,?,?,?)",
        (act.act_id, act.title, act.year, act.act_number, act.language, act.url, act.text),
    )


def upsert_measures(con, act_id: int, m: dict) -> None:
    cols = ["n_words", "n_sections", "obligations", "prohibitions", "permissions",
            "definitional", "penalties", "binding", "binding_per_1000"]
    con.execute(
        f"INSERT OR REPLACE INTO measures (act_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})",
        [act_id] + [m[c] for c in cols],
    )


def replace_citations(con, act_id: int, refs: list[tuple[str, int]]) -> None:
    con.execute("DELETE FROM citations WHERE src_act_id = ?", (act_id,))
    con.executemany(
        "INSERT INTO citations (src_act_id, target_number, target_year) VALUES (?,?,?)",
        [(act_id, n, y) for n, y in refs],
    )


def resolve_citations(con) -> int:
    """Link each citation to an act in the corpus by (number, year). Returns the number resolved."""
    con.execute(
        """UPDATE citations SET target_act_id = (
               SELECT act_id FROM acts
               WHERE acts.act_number = citations.target_number AND acts.year = citations.target_year
               LIMIT 1)"""
    )
    return con.execute("SELECT COUNT(*) FROM citations WHERE target_act_id IS NOT NULL").fetchone()[0]
