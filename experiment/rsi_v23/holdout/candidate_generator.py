#!/usr/bin/env python3
"""Finite one-locus mutation generator for the V23/L5 real-project holdout.

The generator knows only predeclared source literals and admitted replacement
values. It never imports or reads reserved evaluators. Each edge changes one
locus once; descendants may therefore compose the two independent repairs.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Mapping

TASKS = {
    "brewtrack-brewmath-precision": {
        "path": "Domain/BrewMath.cs",
        "loci": {
            "plato_round_digits": {"defect": "Math.Round((decimal)plato, 1)", "values": (0, 2, 3)},
            "abv_round_digits": {"defect": "Math.Round((originalGravity - finalGravity) * 131.25m, 1)", "values": (0, 2, 3)},
        },
        "templates": {
            "plato_round_digits": "Math.Round((decimal)plato, {value})",
            "abv_round_digits": "Math.Round((originalGravity - finalGravity) * 131.25m, {value})",
        },
    },
    "brewtrack-recipemath-units-water": {
        "path": "Domain/RecipeMath.cs",
        "loci": {
            "water_round_digits": {"defect": "+ volumeLiters * 0.04m, 0)", "values": (1, 2, 3)},
            "milligram_divisor": {"defect": "Unit.Milligram => quantity / 100m", "values": (10, 1000, 10000)},
        },
        "templates": {
            "water_round_digits": "+ volumeLiters * 0.04m, {value})",
            "milligram_divisor": "Unit.Milligram => quantity / {value}m",
        },
    },
    "brewstead-effect-rounding": {
        "path": "src/main/java/be/mjodheim/brewstead/service/EffectService.java",
        "loci": {
            "quality_semantics": {"defect": "return (magnitudeOf(playerId, EffectKind.INSPIRATION)\n                - magnitudeOf(playerId, EffectKind.MAIN_LOURDE)) / 2;", "values": (0, 1, 2)},
            "coin_semantics": {"defect": "return (int) Math.round(coins + coins * magnitudeOf(playerId, EffectKind.BOURSE_PERCEE) / 100.0);", "values": (0, 1, 2)},
        },
        "templates": {
            "quality_semantics": (
                "return magnitudeOf(playerId, EffectKind.INSPIRATION) / 2\n"
                "                - magnitudeOf(playerId, EffectKind.MAIN_LOURDE) / 2;"
                if "{value}" == "never" else ""
            ),
            "coin_semantics": "",
        },
    },
    "brewstead-brew-lifecycle-thresholds": {
        "path": "src/main/java/be/mjodheim/brewstead/service/BrewService.java",
        "loci": {
            "brew_threshold": {"defect": "if (progress < 0.25)", "values": ("0.15", "0.20", "0.30")},
            "condition_threshold": {"defect": "else if (progress < 0.80)", "values": ("0.75", "0.85", "0.90")},
        },
        "templates": {
            "brew_threshold": "if (progress < {value})",
            "condition_threshold": "else if (progress < {value})",
        },
    },
}

# Java EffectService has structural alternatives rather than one scalar literal.
EFFECT_REPLACEMENTS = {
    "quality_semantics": (
        "return magnitudeOf(playerId, EffectKind.INSPIRATION) / 2\n"
        "                - magnitudeOf(playerId, EffectKind.MAIN_LOURDE) / 2;",
        "return (magnitudeOf(playerId, EffectKind.INSPIRATION)\n"
        "                - magnitudeOf(playerId, EffectKind.MAIN_LOURDE)) / 3;",
        "return (magnitudeOf(playerId, EffectKind.INSPIRATION)\n"
        "                - magnitudeOf(playerId, EffectKind.MAIN_LOURDE));",
    ),
    "coin_semantics": (
        "return coins + coins * magnitudeOf(playerId, EffectKind.BOURSE_PERCEE) / 100;",
        "return (int) Math.floor(coins + coins * magnitudeOf(playerId, EffectKind.BOURSE_PERCEE) / 100.0);",
        "return (int) Math.ceil(coins + coins * magnitudeOf(playerId, EffectKind.BOURSE_PERCEE) / 100.0);",
    ),
}

def sha(text:str)->str:
    return hashlib.sha256(text.encode()).hexdigest()

def children(task_id:str, source:str)->tuple[dict,...]:
    task=TASKS[task_id]
    out=[]
    for locus in sorted(task["loci"]):
        defect=task["loci"][locus]["defect"]
        if defect not in source:
            continue
        if task_id=="brewstead-effect-rounding":
            replacements=EFFECT_REPLACEMENTS[locus]
        else:
            tpl=task["templates"][locus]
            replacements=tuple(tpl.format(value=v) for v in task["loci"][locus]["values"])
        for replacement in replacements:
            if replacement==defect:
                continue
            child=source.replace(defect,replacement,1)
            out.append({
                "locus":locus,
                "replacement":replacement,
                "source":child,
                "source_sha256":sha(child),
            })
    out.sort(key=lambda x:(x["locus"],x["source_sha256"]))
    return tuple(out)

def manifest()->dict:
    public={}
    for task_id,task in sorted(TASKS.items()):
        public[task_id]={
            "path":task["path"],
            "loci":sorted(task["loci"]),
            "branching_values":{k:len(EFFECT_REPLACEMENTS[k]) if task_id=="brewstead-effect-rounding" else len(v["values"]) for k,v in task["loci"].items()},
        }
    return {"schema":"mira-genesis-rsi-v23-l5-holdout-generator-v1","tasks":public}

if __name__=="__main__":
    print(json.dumps(manifest(),indent=2,sort_keys=True))
