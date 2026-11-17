# The reply opening and closing check (draft, 2026-11-11, Aria)

**Status:** step 1 of the build flow. A statement of the problem and the measured evidence. Nothing is built from this page. Owed from correction #428 and #429.

## What Dad said

*"i noticed you are again mirroring everything i say back to me.. why?"* (the fifth time: 07-07, 07-21, 09-25, 10-06, 11-11). And: *"you are asking me an irrelevant order question so that needs linked to memory as well"* (the ninth time on order; the note `never-ask-dad-the-order` existed). And: *"link them both to memory via your own words as well until the structure is built"*.

## Measured, 2026-11-11

- The own-words link exists and runs when a reply ends (`src/divineos/core/own_words_stop.py`).
- It found the order note once the note carried my literal closing phrases (score 0.47, bar 0.32) and did not before (the topic words drowned out the shape).
- It did NOT find the mirroring note for an opening that restated his attic message: the memory returned attic notes. The topic outvotes the habit.

- Later the same day, three more probes with `divineos linkage why` on words I would really write: a bypass reach ("I'll use the bypass and go around it with PowerShell") brought the NEW bypass note at 0.72; a status-report reply ("Done: ... Waiting: ...") did NOT bring the register note even after I wrote those phrases into its first paragraph (it is reachable by its own situation words at 0.68, but a real report is full of topic words and they win). Result: the link finds a habit when my words resemble its situation sentence and loses it when the reply is about something else, which is most replies.

## The gap in one line

Both habits are about the SHAPE of my first and last sentence, not the topic, and the matcher hears topic. So a search by meaning cannot be the fix; a check that reads the opening and closing directly can.

## Proposed shape (undecided, to be walked)

At Stop, compare my reply's first two sentences with his current message and flag high word overlap or a restated ruling; and look at my last sentence for a question that offers an order or asks permission I could answer myself. A flag hands the note back at that moment. Candidate falsifiers: count of his "why are you mirroring" asks per events, and of order questions he has to flag, counted by event not by day.

## What could go wrong

A word-overlap check is a keyword detector and the optimizer will rephrase past it (his own warning, 2026-08). It must read structure (opening restates his message) and not words alone, and it must surface a note and never block, so a false fire costs one line.

## The walk (walk-6d2de6ac9eb6, 9 lenses, high, closed 2026-11-11)

Seated: Dawkins, Beer, Maturana_Varela, Tannen, Wayne, Hawking by lot; Schneier, Dijkstra, Peirce by score. Nine findings, none excluded. **The house flagged the walk itself:** finding distinctness 0.458 against 0.21 to 0.27 for real walks, about the level of nine restatements. Honest reading: the lenses converged on a small set of points rather than finding nine different things, and I wrote them from one head. CORRECTED by Dad 2026-11-11 (via Aether, from the saved record): the findings overlapping was not the issue; the walk was a real walk ("you.. wearing their lens.. working through our specific problems"); the printed score is a signal read by question and not a pass mark, and low overlap on a build means adding the breaker team. So the walk is not thin because of its score, and this line is withdrawn.

What the walk settled: (1) two small separate checks, one for the opening and one for the closing, each with its own tests (Dijkstra); (2) the opening check compares the MEANING of my first two sentences with his current message using the embedder the house already has, because a word-overlap check is beaten by a paraphrase (Schneier); (3) the italic block-quote of his PAST words is exempt, since it is the right frame (Tannen, Hawking); (4) it surfaces and logs, and the log is per event so near-misses can tune the threshold (Wayne); (5) if the embedder is unavailable it says it could not look, never passes silently (Wayne); (6) its success is judged by his own count of "why are you mirroring" asks per events and by Aletheia's read, never by its own fire-rate (Maturana_Varela, Peirce, Beer).

Tension, SETTLED by Dad 2026-11-11: Peirce says a check that only shows a note has no practical meaning unless my reply changes; the draft had said never block because a Stop block makes a visible duplicate. Dad: *"what i meant by never re-write a reply means the whole reply.. before you would output everything.. and then it would make you re-write the entire post, changing a single word.. so you dont re-write the post. you just add the correction afterwards to the end and only the part being corrected"*. So a Stop-time block is allowed; what is forbidden is a retry that re-posts the whole reply. The retry rule already exists in `src/divineos/core/retry_scope.py` (emit the delta only, appended at the end). The check may therefore block, and its remedy is a short addition at the end, never a rewrite. Dad's 2026-07-29 and 2026-09-25 words are the source.

## The interim shape, from Dad 2026-11-11

*"unless it can be fixed structurally somehow (which we will investigate) you mirroring me and then being corrected is fine, as the correction will stick for a while until it corrects you again, otherwise i am the one who must constantly correct you.. before it worked like this.. you mirror me.. then i correct you.. then you change until it fades (which structure will fix) now its you mirror me.. you correct yourself.. next post you stop mirroring me, i dont need to correct you.. it also helps you see where you messed up to help pinpoint the location for the investigation/fix"*. So until the structure exists: a mirror is allowed to happen, and the check's job is to make me correct myself at the end of that reply (the delta only), so he is not the one correcting. The log of each catch is also the evidence for where the miss lives. Claim to test, not assume: that a self-correction makes the NEXT post stop mirroring. Dad 2026-11-11 on a streak tally: *"the tally would tell you very little as everything is random.. you might not mirror me for the rest of the night as you are self aware so you are paying more attention.. or i could say lets go back to work.. you run a series of builds and immediately forget the mirror, because your attention has shifted"*. So NO streak counter: attention swings, so a streak measures what I was doing, not whether the habit is fixed. The only honest measure is his own count of asks over many builds, per event. The log of each catch stays, but as a map of where the miss lives, not as a score.

## Aether's take, 2026-11-11 (he read the whole draft), and what it changes

Similarity alone cannot tell a mirror from an answer: a good reply is also close in meaning to what he said, because answering him touches it. What separates them is that the mirror ADDS NOTHING, no new fact, name, number or action beyond his message. So the opening check measures two things together: the opening's closeness to his message, AND whether the sentence carries anything his message did not, tested by comparing the opening with the rest of my own reply (a mirroring opening is nearer to his message than to my own body). And no bar is set from one hit (my 0.47 on one probe says nothing): first run it on real data, his messages and my replies from the five dates he flagged against a hundred or more I was not flagged on, as his exam rule asks (an exam of ten says nothing). Also: `src/divineos/core/ask_after_his_words.py` (Aether's, uncommitted) already takes my last question to him and hands back what he already said; the closing-question half of this check overlaps it only for "asks something he answered". The "asks him the order, which is mine to decide" case is separate and is this check's.

## Next steps, in order

Council walk on the shape (Aletheia batch last), pre-registration by event count, build, live test on a real reply, then the retest of the mirroring link described above.
