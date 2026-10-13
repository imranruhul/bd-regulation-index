import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bdreg import db, network  # noqa: E402
from bdreg.measure import cross_references, measure  # noqa: E402
from bdreg.scrape import Scraper, parse_title, roman_to_int  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_roman_numerals():
    assert [roman_to_int(s) for s in ["XII", "XLV", "MCMXC", "7"]] == [12, 45, 1990, 7]


def test_parse_title():
    assert parse_title("The Penal Code, 1860 ( ACT NO. XLV OF 1860 )") == (1860, "45")
    assert parse_title("নমুনা ব্যবসা আইন, ২০১০") == (2010, None)


def test_offline_pipeline(tmp_path):
    s = Scraper(cache_dir=FIXTURES)
    s.base_url = "offline://"
    ids = s.act_ids()
    assert ids == [1, 2, 3]  # duplicates and non-act links dropped

    con = db.connect(tmp_path / "t.sqlite")
    for i in ids:
        act = s.fetch_act(i)
        db.upsert_act(con, act)
        db.upsert_measures(con, i, measure(act.text, act.language).to_dict())
        db.replace_citations(con, i, cross_references(act.text))
    langs = dict(con.execute("SELECT act_id, language FROM acts"))
    assert langs == {1: "en", 2: "en", 3: "bn"}

    nav_text = con.execute("SELECT text FROM acts WHERE act_id = 1").fetchone()[0]
    assert "Home | Laws" not in nav_text  # navigation stripped

    # Act 2 cites Act 1 (Act No. XII of 1950) twice; both resolve.
    assert db.resolve_citations(con) == 2
    g = network.build_graph(con)
    assert g.has_edge(2, 1) and g[2][1]["weight"] == 2
    assert network.most_cited(g).iloc[0]["act_id"] == 1

    by_year = con.execute(db.BY_YEAR_SQL).fetchall()
    assert [row[0] for row in by_year] == [1950, 1975, 2010]
