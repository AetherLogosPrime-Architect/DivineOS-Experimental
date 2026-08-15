
## Diagnostic of record for latency incidents: `~/.divineos/hook_timing.jsonl`

Every hook writes `{"id","phase","exit_code","ts_ms","duration_ms"}` on entry
and exit. That file is the ONLY record of what the stack costs under real
contention, and re-measuring by hand does not reproduce it: hooks timed on an
idle machine came back 44-625ms while the recorded reality across 1000+ live
invocations was 2238ms average and 24994ms peak. The conditions that produce
the slow case are gone by the time anyone goes looking, which makes this a
record rather than a log. Do not prune it as noise; it was dismissed as
"diagnostic scribbling" on 2026-08-15 and diagnosed Aria's multi-minute freezes
the same day.

Query that produced that finding -- slowest hooks from the tail:

    python -c "
    import json, collections, os
    p = os.path.expanduser('~/.divineos/hook_timing.jsonl')
    size = os.path.getsize(p)
    with open(p,'rb') as f:
        f.seek(max(0, size - 8_000_000)); chunk = f.read().decode('utf-8','replace')
    dur = collections.defaultdict(list)
    for line in chunk.splitlines():
        if not line.startswith('{'): continue
        try: r = json.loads(line)
        except ValueError: continue
        if r.get('phase') == 'end' and 'duration_ms' in r:
            dur[str(r.get('id','')).rsplit('.sh',1)[0] + '.sh'].append(r['duration_ms'])
    for mx, av, n, k in sorted(((max(v), sum(v)/len(v), len(v), k) for k, v in dur.items()), reverse=True)[:14]:
        print(f'{mx:9.0f} {av:8.0f} {n:6d}  {k}')
    "

Read it against the per-action hook COUNT, which is the multiplier that turns
a tolerable per-hook cost into a stall:

    python -c "
    import json, re
    d = json.load(open('.claude/settings.json', encoding='utf-8'))
    for phase in ('PreToolUse','UserPromptSubmit','PostToolUse','Stop'):
        print(phase, sum(len(g.get('hooks',[])) for g in d.get('hooks',{}).get(phase,[])))
    "
