"""Replay the frozen M092-B proposal-stream prefix and its cross-process resume boundary."""
from __future__ import annotations

import json

from metamorphosis.m092_search_enumerator import EnumerationAudit, audit_prefix


PREFIX_SIZE = 512
SPLIT_AT = 137


def main() -> int:
    uninterrupted = audit_prefix(limit=PREFIX_SIZE)
    first = audit_prefix(limit=SPLIT_AT)
    restored = EnumerationAudit.from_dict(json.loads(json.dumps(
        first.to_dict(), sort_keys=True, separators=(",", ":"),
    )))
    resumed = audit_prefix(
        limit=PREFIX_SIZE - SPLIT_AT,
        cursor=restored.last_cursor,
        audit=restored,
    )
    if resumed.to_dict() != uninterrupted.to_dict():
        raise SystemExit("resumed M092-B proposal stream differs from uninterrupted replay")
    report = uninterrupted.to_dict()
    report.update({
        "checked_prefix_size": PREFIX_SIZE,
        "resume_split_at": SPLIT_AT,
        "resume_equivalent": True,
    })
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
