# Language policy

English is the only language permitted on the active Mira Genesis surface.

## English-only scope

The rule applies to:

- source code identifiers, comments and docstrings;
- active experiment protocols and status files;
- current results and analysis;
- scripts, tests and workflow labels;
- repository configuration;
- README, project state, roadmap, decisions, measures and failure logs;
- issue and pull-request descriptions created for ongoing research.

New active content must be written in English even when the surrounding legacy file has
not yet been translated. A touched active file should be translated completely rather
than becoming permanently bilingual.

## Historical exception

Files under `archives/` and immutable evidence captured by a consumed canonical run may
retain their original language. They are provenance records. Translating or rewriting
those artifacts would change historical evidence.

A current index or explanation that points to an archive must still be English.

## Migration rule

Legacy active French is technical debt, not an accepted second language. It is removed
incrementally in dedicated pull requests. The target is zero French prose outside
historical archives and quoted immutable evidence.

## Review rule

A pull request introducing non-English active prose should not merge. Scientific terms,
proper names and literal data from an external interface are allowed when translation
would change their identity.
