"""Scrape, measure and store the Laws of Bangladesh, then write summary tables and figures.

Examples
    python scripts/run_pipeline.py --limit 50           # first 50 acts, for a quick test
    python scripts/run_pipeline.py                      # full corpus (slow; polite delay per page)
    python scripts/run_pipeline.py --offline tests/fixtures   # run on the bundled sample pages
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bdreg import db, network  # noqa: E402
from bdreg.measure import cross_references, measure  # noqa: E402
from bdreg.scrape import Scraper  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/bdlaws.sqlite")
    ap.add_argument("--out", default="output")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N acts")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--offline", default=None, help="read cached pages from this folder instead of the web")
    args = ap.parse_args()

    scraper = Scraper(cache_dir=args.offline or "data/cache", delay=args.delay)
    if args.offline:  # never touch the network in offline mode
        scraper.base_url = "offline://"
    con = db.connect(args.db)

    ids = scraper.act_ids()[: args.limit]
    print(f"{len(ids)} acts to process")
    for i, act_id in enumerate(ids, 1):
        try:
            act = scraper.fetch_act(act_id)
        except Exception as e:  # keep going; log and skip pages that fail
            print(f"  skip act {act_id}: {e}")
            continue
        db.upsert_act(con, act)
        db.upsert_measures(con, act_id, measure(act.text, act.language).to_dict())
        db.replace_citations(con, act_id, cross_references(act.text))
        if i % 25 == 0:
            con.commit()
            print(f"  {i}/{len(ids)}")
    resolved = db.resolve_citations(con)
    con.commit()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    by_year = pd.read_sql_query(db.BY_YEAR_SQL, con)
    by_year["cumulative_words"] = by_year["words"].cumsum()
    by_year.to_csv(out / "by_year.csv", index=False)

    g = network.build_graph(con)
    network.most_cited(g).to_csv(out / "most_cited.csv", index=False)
    stats = network.summary(g) | {"citations_resolved": resolved}
    (out / "network_summary.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

    from make_figures import make_figures  # local script
    make_figures(by_year, out)
    print(f"Wrote tables and figures to {out}/")


if __name__ == "__main__":
    main()
