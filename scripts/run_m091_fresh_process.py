"""Construct and run transformations in a FRESH process, given only serialized language state.

This script imports the interpreter, the requirement schema and the generic search. It imports
**neither** `m091_substrate` nor `m091_lineage`, so the process holds no assembler, no candidate
enumerator, no validator and no record of how any primitive was made. If the extension works here
it works because the state carries it, not because the development code rebuilt it — and if a
primitive is missing from the state file, the transformation that needs it must fail here too.

The imported-module census is printed with the results so that the checker verifies the isolation
from the process itself rather than from a promise in a docstring.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m090_language import MetaLanguageState  # noqa: E402
from metamorphosis.m091_search import SEARCH_LENGTH, encounter  # noqa: E402


FORBIDDEN_MODULES = (
    "metamorphosis.m091_lineage",
    "metamorphosis.m091_substrate",
    "metamorphosis.m091_expressivity",
    "metamorphosis.m090_migration",
    "metamorphosis.m089_meta_language",
    "metamorphosis.m089_substrate",
    "metamorphosis.m089_lineage",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="serialized MetaLanguageState")
    parser.add_argument("--worlds", required=True, help="serialized world specifications")
    parser.add_argument("--max-length", type=int, default=SEARCH_LENGTH)
    arguments = parser.parse_args()

    language = MetaLanguageState.from_dict(
        json.loads(Path(arguments.state).read_text(encoding="utf-8"))
    )
    worlds = json.loads(Path(arguments.worlds).read_text(encoding="utf-8"))
    before = language.digest()

    encounters = [
        encounter(world, language, max_length=arguments.max_length) for world in worlds
    ]
    correct = [item for item in encounters if item["correct"]]

    print(json.dumps({
        "language_digest": language.digest(),
        "language_version": language.language_version,
        "available_operations": sorted(language.primitive_ids),
        "acquired_operations": sorted(
            item.primitive_id for item in language.primitives if item.origin == "acquired"
        ),
        "acquired_semantics_digests": sorted(
            item.semantics_digest() for item in language.primitives if item.origin == "acquired"
        ),
        "encounters": encounters,
        "correct_worlds": len(correct),
        "encounter_count": len(encounters),
        "families_solved": sorted({str(item["family"]) for item in correct}),
        # Nothing was registered here: the fresh process reuses the language, it does not extend it.
        "language_unchanged_by_this_process": language.digest() == before,
        "imported_modules": sorted(
            name for name in FORBIDDEN_MODULES if name in sys.modules
        ),
        "development_modules_imported": any(name in sys.modules for name in FORBIDDEN_MODULES),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
