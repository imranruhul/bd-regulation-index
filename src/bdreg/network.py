"""Citation network between laws: which acts cite which, and which are most central."""
from __future__ import annotations

import networkx as nx
import pandas as pd


def build_graph(con) -> nx.DiGraph:
    g = nx.DiGraph()
    for act_id, title, year in con.execute("SELECT act_id, title, year FROM acts"):
        g.add_node(act_id, title=title, year=year)
    rows = con.execute(
        "SELECT src_act_id, target_act_id FROM citations "
        "WHERE target_act_id IS NOT NULL AND target_act_id != src_act_id"
    )
    for src, dst in rows:
        w = g[src][dst]["weight"] + 1 if g.has_edge(src, dst) else 1
        g.add_edge(src, dst, weight=w)
    return g


def summary(g: nx.DiGraph) -> dict:
    n = g.number_of_nodes()
    return {
        "acts": n,
        "citation_links": g.number_of_edges(),
        "density": round(nx.density(g), 5) if n > 1 else 0.0,
        "share_cited_at_least_once": round(sum(1 for v in g if g.in_degree(v) > 0) / n, 3) if n else 0.0,
    }


def most_cited(g: nx.DiGraph, k: int = 10) -> pd.DataFrame:
    pr = nx.pagerank(g, weight="weight") if g.number_of_edges() else {v: 0.0 for v in g}
    df = pd.DataFrame(
        [(v, g.nodes[v]["title"], g.nodes[v]["year"], g.in_degree(v), pr[v]) for v in g],
        columns=["act_id", "title", "year", "cited_by", "pagerank"],
    )
    return df.sort_values(["cited_by", "pagerank"], ascending=False).head(k).reset_index(drop=True)
