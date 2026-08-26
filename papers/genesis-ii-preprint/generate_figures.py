#!/usr/bin/env python3
"""Generate the Genesis II manuscript figures from frozen, cited summary values.

The values in figure_data.json are transcriptions of preserved M107--M112 artifacts.
This script does not re-run experiments or tune parameters.
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
DATA = json.loads((ROOT / "figure_data.json").read_text(encoding="utf-8"))


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def chain_figure() -> None:
    fig, ax = plt.subplots(figsize=(12.8, 3.2))
    ax.set_axis_off()
    items = [
        ("M107 / D076", "Interpreter extension\n4 -> 16 Boolean functions"),
        ("M108 / D077", "Acquisition-machinery\nattribution rule"),
        ("M109 / D078", "Second machinery generation\nReach 6 < 20 < 243"),
        ("M110 / D079", "Cross-carrier transfer\nand measured harm"),
        ("M111 / D080", "Self-directed diagnosis\nrecursive depth three"),
        ("M112 / D081", "Blind sealed world bank\nmixed: 24/24, 22/24"),
    ]
    xs = [i * 1.55 for i in range(len(items))]
    compact = [
        ("M107 / D076", "Interpreter\nextension\n4 -> 16"),
        ("M108 / D077", "Acquisition\nmachinery rule"),
        ("M109 / D078", "Second machinery\ngeneration\n6 < 20 < 243"),
        ("M110 / D079", "Cross-carrier\ntransfer + harm"),
        ("M111 / D080", "Self-directed\ndiagnosis\ndepth three"),
        ("M112 / D081", "Blind sealed\nworld bank\n24/24; 22/24"),
    ]
    for x, (head, body) in zip(xs, compact):
        ax.text(
            x, 0, f"{head}\n{body}",
            ha="center", va="center", fontsize=8.4,
            bbox=dict(boxstyle="round,pad=0.45"),
        )
    for left, right in zip(xs[:-1], xs[1:]):
        ax.annotate("", xy=(right - 0.55, 0), xytext=(left + 0.55, 0),
                    arrowprops=dict(arrowstyle="->", lw=1.35))
    ax.set_xlim(-0.8, xs[-1] + 0.8)
    ax.set_ylim(-1, 1)
    ax.set_title("Genesis II: the experimental chain M107-M112", fontsize=12)
    save(fig, "fig1_chain")


def capacity_competence() -> None:
    d = DATA["capacity_competence"]
    arms = d["arms"]
    mins = d["reach_min"]
    maxs = d["reach_max"]
    mids = [(a + b) / 2 for a, b in zip(mins, maxs)]
    low = [m - a for m, a in zip(mids, mins)]
    high = [b - m for b, m in zip(maxs, mids)]

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    x = range(len(arms))
    ax.errorbar(x, mids, yerr=[low, high], fmt="o-", capsize=7, linewidth=1.8)
    ax.set_ylim(70, 620)
    align = ["left", "center", "right"]
    offsets = [(4, 10), (0, 10), (-4, 10)]
    for i, solved in enumerate(d["row5_solved_of_6"]):
        ax.annotate(f"row-5 competence: {solved}/6", (i, maxs[i]),
                    xytext=offsets[i], textcoords="offset points", ha=align[i], fontsize=9)
    ax.set_xticks(list(x), arms)
    ax.set_ylabel("ReachImprove size (recorded min-max across six worlds)")
    ax.set_title("Capacity rises while row-5 competence falls")
    ax.grid(axis="y", alpha=0.25)
    save(fig, "fig2_capacity_competence")


def expressibility() -> None:
    d = DATA["expressibility"]
    arms = d["arms"]
    rule = d["policy_rule_space"]
    sep = d["separating_programs"]
    x = list(range(len(arms)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.bar([v - width/2 for v in x], rule, width, label="policy rule space")
    ax.bar([v + width/2 for v in x], sep, width, label="separating programs")
    for i, val in enumerate(rule):
        ax.text(i - width/2, val + 3, str(val), ha="center", fontsize=9)
    for i, val in enumerate(sep):
        ax.text(i + width/2, val + 3, str(val), ha="center", fontsize=9)
    ax.set_xticks(x, arms)
    ax.set_ylabel("Program count")
    ax.set_title("Generation two creates diagnostic-policy expressibility")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    save(fig, "fig3_expressibility")


def blind_closure() -> None:
    d = DATA["blind_closure"]
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.plot(d["bounds"], d["image_size"], marker="o")
    for x, y in zip(d["bounds"], d["image_size"]):
        ax.annotate(str(y), (x, y), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.set_xticks(d["bounds"])
    ax.set_xlabel("Fixed-point node bound")
    ax.set_ylabel("Constructive image size")
    ax.set_title("Blind M112 world: bound 7 was not yet a fixed point")
    ax.text(0.5, 0.12,
            f"Across {d['project_worlds_checked']:,} project-generated worlds, bound 7 had always sufficed.",
            transform=ax.transAxes, ha="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3"))
    ax.grid(alpha=0.25)
    save(fig, "fig4_blind_closure")


if __name__ == "__main__":
    chain_figure()
    capacity_competence()
    expressibility()
    blind_closure()
