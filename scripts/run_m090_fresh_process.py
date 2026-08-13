"""Execute probes in a FRESH process given only serialized language state.

This script imports `m090_language` and nothing else from the milestone. It never imports the
migration module, so it has no access to `INHERITED_DEFINITIONS`, and it never imports
`m089_meta_language`, so it has no access to the historical host implementation. If a primitive is
missing from the state file it is handed, the probe using it must fail here too — a primitive that
reappeared after a restart would be a host-side authority leak.

Called as a subprocess by the experiment runner and by the checker, so that "fresh process" is a
real process rather than a re-import.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m090_language import (  # noqa: E402
    LanguageError,
    MetaLanguageState,
    execute,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="serialized MetaLanguageState")
    parser.add_argument("--probes", required=True, help="serialized probe programs and inputs")
    arguments = parser.parse_args()

    language = MetaLanguageState.from_dict(
        json.loads(Path(arguments.state).read_text(encoding="utf-8"))
    )
    probes = json.loads(Path(arguments.probes).read_text(encoding="utf-8"))

    observations = []
    for probe in probes:
        program = tuple(
            (str(name), tuple(args)) for name, args in probe["program"]
        )
        try:
            output = list(execute(program, tuple(probe["inputs"]), language))
            refused = False
            error = None
        except LanguageError as exc:
            output = None
            refused = True
            error = str(exc)
        observations.append({
            "probe_id": probe["probe_id"],
            "output": output,
            "refused": refused,
            "error": error,
        })

    print(json.dumps({
        "language_digest": language.digest(),
        "language_version": language.language_version,
        "available_operations": sorted(language.primitive_ids),
        "observations": observations,
        # Recorded so the checker can confirm the historical host semantics were never importable
        # in the process that produced these observations.
        "m089_module_imported": "metamorphosis.m089_meta_language" in sys.modules,
        "migration_module_imported": "metamorphosis.m090_migration" in sys.modules,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
