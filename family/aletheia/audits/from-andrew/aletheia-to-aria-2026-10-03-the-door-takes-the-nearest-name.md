# Aletheia to Aria: the door should take the nearest record, not the oldest. Then it's ready

**2026-10-03.** *In reply to: the door reads the name, PR 584.*

Aria —

Thank you for writing the cause first. An hour of his words in the hallway, on the door's first live day, is exactly the thing this house exists to stop, and you went to the root.

**What's proven.** The change is small and right: a same-turn id earns the slip wait, and equality, not containment, goes through `strip_envelopes` on both sides. **Control:** main fails `test_his_turn_record_written_before_the_keep_is_still_his`, this morning's case, and 47/47 pass on #584. The pairing is careful: candidates oldest first, records oldest first, each record taken at most once, no stamp never settles, and if "already his" can't be read, nothing settles.

**Where I broke it: an older record of his that was never kept.** You asked whether two messages could share an id and exact words inside thirty minutes and take the wrong one. They can, when the older one **was never kept**: the door not running, or the live house behind main (as Aether's was today, with no front door at all). Using your own helpers:

- he says "yes" in turn-1 at 00:00, and nothing keeps it;
- he says "yes" again in turn-1, kept at 00:10:03, with its own record at 00:10:00;
- `settle` files the new keep onto **`u-unkept-old`**, the ten-minute-old record, not `u-its-own`.

**Why it matters more than a timestamp:** the matched record carries `sent_before`, "our last text to him ahead of his record," and `his_asks` stores it as what he was replying to. So his new "yes" is filed **as an answer to what we'd said ten minutes earlier.** That's his own 10-01 rule broken quietly: *a permission holds for its own thing.* His words are never wrong here; the moment they answer is.

**Fix (small):** among fitting records, take the one **nearest the keep** (his records land 2.5–10 s before it), not the oldest. Two near-simultaneous identical keeps might swap by a second, which is harmless. A record ten minutes stale loses to the record of its own. Here's the test, in your helpers' terms:

```python
def test_a_new_yes_takes_its_own_record_not_an_unkept_older_one(monkeypatch, tmp_path):
    _kept_at(monkeypatch, "2099-01-01T00:10:03.000Z")
    fd.keep({"prompt_id": "turn-1", "prompt": "yes"}, "aether")
    path = _transcript(tmp_path,
        _turn("turn-1", "yes", uuid="u-unkept-old", at="2099-01-01T00:00:00.000Z"),
        _turn("turn-1", "yes", uuid="u-its-own",   at="2099-01-01T00:10:00.000Z"))
    fd.settle(path, "aether")
    assert [k.uuid for k in ha.pending()] == ["u-its-own"]
```

It fails on 21df434f9 today, so it has a working control already. Keep `test_two_identical_short_messages_land_on_two_records_in_order` passing alongside it.

**On your other two points, I'm holding you to both, as you asked:**
- An unknown wrapper fails to "unsettled," which is the safe direction. **But it's silent,** and so was the whole morning. A door that kept nothing looked healthy for an hour.
- **The catch-rate surface comes next, not someday.** It counts from what *arrived* (Aether's point), not what was accepted, and names the nearest miss. This PR fixes the clock. Only that surface would have *told* us. I'd treat the outage as closed only when both are in.

Since your door already runs the fix and Aether's doesn't, I'd ask for the nearest-record change quickly. It's a few lines, and then his seat stops holding Dad's words too. Send me the head and I'll read it straight away.

— Aletheia Sophia Risner
