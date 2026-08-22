# Pre-registration: named-mutex singleton primitive + orphan-Monitor cleanup tool will structurally solve the duplicate-Monitor-process accumulation problem Andrew named 2026-06-13 (orphan bash.exe / python.exe processes from prior sessions accumulating because the harness loses task records on resume, with no kernel-level guard against the next re-arm spawning duplicates)

- **ID**: `prereg-90c40ab2d10f`
- **Filed by**: agent
- **Filed at**: 2026-06-12 22:15 UTC
- **Review at**: 2026-07-12 22:15 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-07-12 22:43 UTC

## Claim

Windows named-mutex (CreateMutex / OpenMutex via pywin32) replaces the broken PowerShell regex-self-match approach with a kernel-managed primitive: new arming refuses cleanly if mutex held, kernel releases mutex on process death (even crash), no stale-file possible

## Success criterion

30 days from filing, no observed sessions where I narrate or hit the duplicate-Monitor-accumulation pattern. divineos monitor status correctly reports armed/not-armed via is_held() in every session. divineos monitor cleanup-orphans --kill operator-invoked at least once successfully on legacy orphans, deleting them and freeing system resources

## Falsifier

duplicate Monitor processes continue accumulating despite the mutex (proves pywin32 CreateMutex behavior diverges from MS docs in this environment), OR is_held() reports stale armed state (kernel doesn't release mutex as documented), OR the orphan cleanup --kill fails on legacy bash processes (proves cmdline-scan is insufficient even for sweep)

## Outcome notes

30-day window closed 2026-07-12. Partial verification: Monitor kernel-mutex singleton-guard IS working — observed tonight when re-arming compaction monitor, got [MONITOR-SINGLETON-DEDUP role=compaction occupant=Aether] sibling already alive exiting without arming. That confirms mutex behavior in this environment. What did NOT get exercised: divineos monitor cleanup-orphans --kill on legacy orphans. Cannot honestly claim SUCCESS because success criterion required cleanup-orphans invocation. Filing INCONCLUSIVE — mutex works, cleanup path not exercised in-session. Not a falsifier hit either.
