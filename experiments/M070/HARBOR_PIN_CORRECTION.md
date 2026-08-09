# M070 Harbor release pin correction

This append-only correction was recorded before either selected task was executed.

The frozen selection protocol labels
`f75477f2ad0b04fad199b0cb80689cc23a06c72d` as the Harbor v0.20.0 commit. It is
actually the annotated tag object. The tag peels to executable source commit
`459ff6ec99417589b7f679d14ddf3b3f0ae4f1dc`, whose tree is
`09557fdc853ce5826f5b69643034ac20d1ff80b6`.

The frozen file is intentionally not rewritten. This correction changes no benchmark choice,
selection rule, selected identifier, agent design or scientific result; it makes the harness
provenance unambiguous.
