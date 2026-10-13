"""Two figures: the stock of law in force by year of enactment, and binding language per 1,000 words."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


def make_figures(by_year: pd.DataFrame, out: Path) -> None:
    if by_year.empty:
        print("No data to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(by_year["year"], by_year["cumulative_words"] / 1e6, color="#1f3a5f")
    ax.set_xlabel("Year of enactment")
    ax.set_ylabel("Cumulative words (millions)")
    ax.set_title("Laws in force today, cumulated by year of enactment")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "cumulative_words.png", dpi=150)
    plt.close(fig)

    decade = by_year.assign(decade=(by_year["year"] // 10) * 10).groupby("decade")[["binding", "words"]].sum()
    decade["per_1000"] = 1000 * decade["binding"] / decade["words"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(decade.index, decade["per_1000"], width=8, color="#1f3a5f")
    ax.set_xlabel("Decade of enactment")
    ax.set_ylabel("Binding terms per 1,000 words")
    ax.set_title("Restrictiveness of laws in force, by decade of enactment")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "binding_per_1000_by_decade.png", dpi=150)
    plt.close(fig)
