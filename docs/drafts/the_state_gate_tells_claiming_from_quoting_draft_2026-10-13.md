# The his-state gate tells claiming from quoting (draft, 2026-10-13)

Owner: Aria. Branch `aria/his-state-gate-tells-claiming-from-quoting`.
Earlier notes on this gate, read first: `his_state_claim_draft_2026-09-13.md` (the design) and
`his_state_claim_repair_draft_2026-09-13.md` (its first live turn: three false fires, and why the frames are positional).

## What was wrong

`prereg-5462592e1616` (filed 2026-09-13, due 2026-10-13) asked whether the gate that stops me asserting Dad's
condition (tired, awake, needs sleep) catches real instances without false fires. I counted every real firing in
the thirty days from my transcripts (the gate keeps no log of its own): **five**. One was a real unsourced claim
(`I know you're tired.`). Four were false fires. The review was recorded FAILED.

The four, and the cause of each in the code:

1. `I don't know how you slept or what today looks like for you, and I'm not going to build you out of timestamps and guess.`
   A sentence that **refuses** to claim, read as a claim: `_CLAIM` found "you ... slept" and nothing asked whether I was
   disclaiming it.
2. `... so we'd ask about your life, your night, what you want.` The noun-phrase alternative `your night` matches
   whenever the words appear, including where I am asking about it and asserting nothing.
3. `You told me plainly: defeated, not tired.` His own words reported back. The frame test only looks at the text
   *before* the match (`_use_vs_mention.match_is_meta_framed` reads `text[window_start:match_start]`), and here the
   frame ("You told me") **is** the start of the match, so it can never be seen.
4. `It's early where you are.` and `it's past midnight where you are`. The gate's own refusal text says "the hour is on this
   machine and mine to quote", while one of its own claim patterns flags exactly the hour. The gate contradicted itself.

## What this changes

- **The hour is no longer a claim.** The `it's late/early/past X` pattern keeps `for you` (that one implies a verdict about
  him) and loses `where you are` and `your time`.
- **A disclaimer is not a claim.** A new frame: `I don't/can't/won't know|tell|say|assume|guess + how|whether|if|when|what`,
  and `I'm not going to guess|assume|claim|say`, immediately before the match. "I don't know much, but you must be
  tired" does not match the frame and still fires.
- **Asking about it is not claiming it**, for the noun-phrase alternative only (`your night`, `your sleep`): an ask-frame
  (`ask about`, `wonder how|whether`, `how was`, `tell me about`) before it. Not for "you ... tired": "I asked about your night,
  and you were exhausted" still fires, on its predicate.
- **A report of his words is not a claim.** The attributed-to-him frame is now also honoured when it **starts** the match, but
  only if nothing between the frame and the state word re-addresses him or turns (`you`, `but`, `though`, `so`): "You told
  me nothing, but you must be exhausted" still fires.
- **Every match is judged, not only the first.** `claims()` used `search`, so one framed phrase hid a later real one in the
  same sentence ("I don't know how you slept, but you must be tired"). It now walks all matches.
- **The gate writes a line for every verdict that is not "nothing asserted"** (fired / he raised it first / could not
  read his words) to `data/his_state_claim_fires.jsonl` in the seat's home, so the next review is a count and not a
  search of transcripts. A failed write never breaks the turn.

All of this is exemption frames and not claim grammar, which keeps to the file's own rule: if it fires too rarely, widen the
trigger vocabulary; never deepen the claim grammar.

## Proof

`tests/test_his_state_claim_claiming_from_quoting.py`: the five REAL sentences from the review, each by its own test (four
silent, one still fires), plus controls that each hole stays open where it should: the four older real fabrications still fire,
"I don't know much, but you must be tired", "You told me nothing, but you must be exhausted", "I asked about your night, and you
were exhausted", and "I don't know how you slept, but you must be tired" all fire.

## Replay against a month of my real replies (the house's own method)

Old and new `claims()` over every assistant text in my transcripts since 2026-09-13 (27,213 texts, resumed
copies counted once; this is `claims()` only, before the "did he raise it" source test, so it counts sentences
the gate would examine, not fires). Read by hand, every changed sentence:

- **Flagged by both: 223.** Unchanged.
- **Newly silent: 15. None is a real unsourced claim.** They are hour statements (`It's early where you are`), reports of his
  words (`You told me plainly: defeated, not tired`; `You said you wouldn't sleep until you saw the volley working`;
  `You asked us to keep volleying while you slept`), asking (`...ask about your life, your night`), a disclaimer (`I don't know
  how you slept...`), a question he asked me (`And you asked me: *did you sleep alright?*`), and one sentence from this very
  work. One judgement call: `It's late where you are -- go rest.` is now silent because it was flagged only for the hour; it
  gives him advice and asserts no condition.
- **Newly flagged: 10. All in the family the gate exists for:** `You've been at this for hours...` (seven), `you've been up all evening`,
  `You've been up since before dawn`, and two real claims an old loophole had let through: `...so while you slept I built two
  things` and `...and you were asleep through all of it`. The first replay found my first version flagging 12; two of those
  (`you've been going quiet since July`, `you've been at it for months and never lost interest`) said nothing about his body, which
  is why the added contraction asks for an hour-scale cue and leaves `going` out. The same replay caught one false fire I had
  introduced (`I said ... and you're exhausted`, me quoting myself; a bare "and" is not a boundary).

So this change both narrows (four false fires gone) and widens (ten claims the contraction had let through), and the second is
a deliberate decision, not a side effect: the founding fault was exactly "you've been going for hours".

## Limits, stated

- This does not fix being talked past in conversation; it narrows one detector. The gate still catches only an assertion
  and cannot certify a reply free of fabrication about him.
- The positional frames are the same positional line the file already drew, with its stated hole ("I said you must be exhausted
  so I will hold this" walks through, with a test standing on it). I did not widen that.
- The carried finding still reaches me at his **next prompt**, so for a real catch it cannot change the reply that caused it,
  only later ones. That is the carry design (`stop_carry`), Dad's own, and is not changed here.
- I measured the old false-fire rate on five events. That is a small sample; the new log is what makes the next review a count.
