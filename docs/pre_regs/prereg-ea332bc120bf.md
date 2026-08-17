# Pre-registration: core/dark_matter.py: a structural sweep for things that exist but nothing reaches -- dead hooks and commands prescribed in gate text that do not resolve

- **ID**: `prereg-ea332bc120bf`
- **Filed by**: agent
- **Filed at**: 2026-08-02 02:55 UTC
- **Review at**: 2026-09-01 02:55 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The wiring-gap pattern has been filed since 2026-05-11 and rediscovered repeatedly because it has no consumer. Unlike the semantic questions this substrate cannot decide, reachability is structural -- is this hook named anywhere, does this command resolve against the live Click tree -- so it can be closed mechanically rather than approached.

## Success criterion

On any current invocation, with no waiting: (a) the sweep reports 'divineos psf mark-done' as unresolvable, since it is prescribed by pipeline_gates.py mid-line and has never existed; (b) a valid command such as 'divineos audit export' is never reported; (c) prose containing the word divineos in a sentence is never reported; (d) a hook reachable only from another hook is not called dead, and an underscore-prefixed sourced library is not called a hook; (e) format_report prints every BLIND_SPOTS entry and the line about silence not meaning coverage, on a CLEAN sweep as well as a dirty one; (f) 'divineos dark-matter --check' exits 1 when findings exist and 0 when they do not.

## Falsifier

Any of, each checkable on a single run: (1) the psf case stops being reported, which would mean a precision change has again dropped the motivating case -- this already happened once during construction and is the specific regression to watch; (2) a valid registered command appears in the findings; (3) a clean report omits the blind-spot section, since a detector silently read as exhaustive is worse than no detector; (4) any verdict becomes decidable by a pattern rather than by membership in the registered-command set, which would make this a keyword gate rather than a structural check; (5) the finding count grows large enough that the report is skimmed rather than read -- noise is how a real finding becomes wallpaper, and if that happens the correct response is to cut a detector, not to soften it.
