# bd-regulation-index

A small pipeline that measures how much binding law Bangladesh has, and how restrictive it is.

It scrapes the consolidated laws published on the official
[Laws of Bangladesh](http://bdlaws.minlaw.gov.bd) portal, stores them in SQLite,
and builds three kinds of measures for each law:

| Measure | What it captures |
| --- | --- |
| **Volume** | Words and numbered sections |
| **Restrictiveness** | Obligations (*shall*, *must*, *is required to*) and prohibitions (*shall not*, *no person shall*, *is prohibited*) per 1,000 words |
| **Cross-references** | Citations to other laws by number and year (e.g. *Act No. XLV of 1860*), linked into a citation network |

## Why

Governments promise to cut red tape, but rarely measure how much regulation exists.
Page counts treat a definition and a prohibition as equal. This project separates
text that binds from text that only defines or organises the law. Definitional uses
such as *shall mean* and *shall include* are removed before binding terms are counted.

## Design choices

- **Polite scraping.** One request every 1.5 seconds by default, an identifying
  user agent, and an on-disk cache so no page is fetched twice.
- **SQL storage.** Tables for `acts`, `measures` and `citations`. Aggregates by
  year are computed in SQL (`BY_YEAR_SQL` in `src/bdreg/db.py`).
- **Two languages.** Laws enacted since 1987 are in Bangla. The tool detects the
  language of each text and applies a separate Bangla lexicon
  (*করিবে*, *করিতে হইবে*, *করা যাইবে না*, *নিষিদ্ধ*).
- **Order-aware counting.** Each pattern's matches are removed after counting,
  so *shall not* is never also counted as *shall*, and *fine which may extend*
  is never counted as a permission.
- **Tested.** Unit tests cover the counting rules, Roman-numeral act numbers,
  Bangla digits, citation resolution and the full pipeline on sample pages.

## Usage

```bash
pip install -r requirements.txt
pytest -q                                          # run the tests

python scripts/run_pipeline.py --offline tests/fixtures   # sample pages, no network
python scripts/run_pipeline.py --limit 50                 # first 50 laws from the portal
python scripts/run_pipeline.py                            # full corpus (several hours)
```

Outputs go to `output/`:

- `by_year.csv`: laws, words and binding terms by year of enactment
- `most_cited.csv`: laws most cited by other laws (in-degree and PageRank)
- `network_summary.json`: size and density of the citation network
- `cumulative_words.png`, `binding_per_1000_by_decade.png`

## Limitations

- The corpus is the law **in force today**. Repealed laws are absent, so the
  series by year of enactment is not the historical stock of law.
- The lexicons are a first pass. They need validation against a hand-coded sample
  of provisions. For example, *shall be punishable* is counted as an obligation,
  and the Bangla future tense *করিবে* is not always mandatory.
- Statutory instruments (rules, SROs) are not on the portal and are not covered.
- Selectors in `src/bdreg/scrape.py` match the site layout when written; check
  them if the site changes.
- The pages in `tests/fixtures/` are **synthetic samples** written for testing.
  They are not official texts.

## Next steps

- Validate the lexicons on a random sample of 200 sections.
- Track amendment churn by comparing cached versions of each law over time.
- Map laws to industries to link regulatory text with firm-level data.

## Author

Al-Imran Ruhul Islam · alimranbd@gmail.com · [LinkedIn](https://www.linkedin.com/in/imranruhul)
