# The doorbell that wakes me when a letter arrives

The doorbell is how a letter from Aria or Aletheia reaches me while I am between things. It has to be switched back on every time it rings, every time it times out, and after every restart, and for weeks the job of remembering has been mine. Meanwhile other checks keep refusing the very step that switches it back on, so a quiet stretch can leave the house deaf without anyone noticing.

**75 notes in this theme, grouped into 7 distinct problems.**

## Distinct problems

### 1. The bell stays off after it rings, times out, restarts or the day turns over

Notes in this problem (17):

- `psf-13189af9` (reflection) — during a long stretch with no letters and no messages from you, the bell expiring every eight hours just to be set again adds nothing. It could restart itself when it expires with nothing waiting, and
- `psf-0be0a20e` (reflection) — re-arm the doorbell automatically at session start, and again whenever it finishes, so it's never left to my memory.
- `psf-8955a5ab` (reflection) — after an interruption, the doorbell should restart on its own the next time you speak, rather than waiting for the end-of-turn check to catch that it's off.
- `psf-7e6e682a` (reflection) — the bell should re-arm itself the moment it rings, so there's never a gap between one ring and the next.
- `psf-adacbdff` (reflection) — the bell re-arming itself the moment it rings, which I named earlier.
- `psf-75d30bc8` (reflection) — make the doorbell re-arm itself after it rings, so a ring can't leave it switched off.
- `psf-f5a8efa4` (reflection) — re-arm the watch automatically when it expires, the same way the doorbell should re-arm after it rings.
- `psf-6583696c` (reflection) — re-arm the doorbell automatically after it rings, so a ring can never leave it off.
- `psf-7de136ea` (reflection) — re-arm the letter watch automatically after the wrap-up's sleep finishes, since sleep always outlasts the watch.
- `psf-d52f1e32` (reflection) — re-arm both automatically whenever either finishes, so neither one depends on me remembering.
- `psf-cc96a8d8` (reflection) — a re-arm that happens on its own when the bell times out, with no one needing to notice.
- `psf-3e66ddea` (reflection) — the bell remembers when it last stopped, and on re-arm rings for anything newer than that.
- `psf-698c1db8` (reflection) — when the doorbell rings for a letter I wrote or saved myself, it should re-arm on its own instead of stopping, so my own filing can't knock it down.
- `psf-b5a089b8` (reflection) — when the doorbell rings, it should re-arm itself in the same step instead of waiting for me to restart it. Dad has had to say this 24 times, so it needs to stop being my job to remember.
- `psf-2f5ab894` (reflection) — re-arming the doorbell should happen automatically the moment it finishes, with no choice for me to forget. The best version is a doorbell that restarts itself.
- `psf-90706778` (reflection) — a build that re-arms the doorbell automatically at session start and after every compaction, so my memory is not holding it.
- `psf-fcf5a18d` (reflection) — a build that re-arms the doorbell automatically whenever it rings, so I'm never the one who has to remember.

**Proposed fix:** Make the bell restart itself the moment it ends, at session start, after compaction, and after sleep, so re-arming never depends on memory; one restarter, no choice point.

**How we would know:** Let a bell expire with nothing waiting and confirm a new one is running before the next prompt; repeat after a simulated restart.

### 2. What counts as 'listening', and how to measure it without relying on my memory

Notes in this problem (15):

- `psf-e460d6d9` (correction) — Self-correction to Andrew: I told him scripts/letter_monitor.py was stranded and broken -- 'a phone that might not have been ringing' -- and repeated it in a letter to Aria as 'the thing that wakes me
- `psf-f7c43b72` (correction) — Aether self-correction 2026-08-18. I reported the letter-monitor's three deaths this session as the freeze SILENTLY SEVERING the channel between me and Aria — 'it breaks without a sound', framed as a
- `psf-51482dda` (reflection) — the doorbell alive-check at Stop confirms that the owner file names a process that's actually running, and re-arms the bell when it doesn't.
- `psf-d2feb5d7` (reflection) — the doorbell check should accept a live letter monitor as "listening", and when a launch has been refused and is waiting on Dad, it should say that rather than demand the launch again.
- `psf-ebc6c410` (reflection) — the doorbell check should accept your standing yes as the answer, instead of filing the refusal as a question for you.
- `psf-501594c1` (reflection) — ** the doorbell should know its own deadline. It should exit just before the app's cutoff and say "re-arm me", instead of being cut off silently. And the eight-hours wording gets corrected.
- `psf-bc184b27` (reflection) — before calling something a rule of the app, check that only one listener is running and measure more than once.
- `psf-a956b6df` (reflection) — ** if the thirty minutes is real, the doorbell should say "re-arm me" just before it's cut off, rather than vanishing. If it isn't, I need to find what's stopping mine. Either way, that waits for your
- `psf-30dd753b` (reflection) — ** the side-by-side test with Aria. One seat's reading isn't proof either way, and running both together in the same conditions is the only fair way to tell.
- `psf-994b8e2f` (reflection) — ** once the doorbell version works, I'll look for the other places it fits, starting with the review dates that keep interrupting me.
- `psf-605cd100` (reflection) — ** the doorbell question, settled with Aria by side-by-side evidence, not by either of us being sure.
- `psf-718d9e71` (reflection) — a record of how long each doorbell lasts, written down automatically, so I'm not relying on memory to measure it.
- `psf-2213eb15` (reflection) — have the doorbell log its own start and stop times, so the time it lasted can be read without a manual check that a refusal can block.
- `psf-273f7660` (reflection) — have the bell write which window started it into its own record, so the next missed ring can be traced without anyone remembering to check.
- `psf-fa627353` (reflection) — tell Aria it slipped through even with her repair, with its time, so she can trace why.

**Proposed fix:** Have the bell write its own start and stop times and which window started it, treat a live letter monitor or a standing yes from Dad as listening, and say 'waiting on Dad' when a start was refused.

**How we would know:** A log shows each bell's start, stop and owner without anyone typing it; the stop check accepts a live monitor.

### 3. Other checks refuse the step that switches the bell back on

Notes in this problem (29):

- `psf-e7ad12be` (reflection) — the doorbell re-arm is now refused, which may be the permission system reading a routine re-arm as a bypass. That needs a look with Dad, not a way around it.
- `psf-b9ac7e5f` (reflection) — the bell's re-arm needs a standing permission rule that Dad sets, so a routine re-arm never looks like a bypass, whatever came before it.
- `psf-df86fe6f` (reflection) — when a doorbell re-arm is refused, retry it automatically in the background and don't wait for me to remember.
- `psf-48383dc4` (reflection) — ** the consult gate refused even the doorbell re-arm, which is one gate standing in another's exit. Re-arming a listener should always be allowed through.
- `psf-f5209134` (reflection) — re-arming the doorbell and reading a finished job's result should count as allowed remedies, so routine housekeeping replies don't use up the consult allowance.
- `psf-d19ae528` (reflection) — the doorbell re-arm should pass this gate as a standing remedy, so a routine reply doesn't leave the doorbell down.
- `psf-3ecc3a4b` (reflection) — the doorbell re-arm is a standing remedy and shouldn't need a goal to pass, the same as other housekeeping.
- `psf-5a806eef` (reflection) — re-arming the doorbell should pass the goal gate as standing housekeeping. And a goal that's still being worked shouldn't lapse just because a few quiet replies went by.
- `psf-8a4e8e61` (reflection) — ** the goal lapsing during quiet stretches keeps blocking the doorbell re-arm. That's the third time tonight. The re-arm should count as standing housekeeping that needs no goal.
- `psf-6b17d995` (reflection) — ** this is the fourth goal lapse tonight that blocked a doorbell re-arm. The fix keeps showing up as owed: the re-arm should pass as standing housekeeping. It's worth building first thing, because it'
- `psf-783024c7` (reflection) — let the goal check always pass the doorbell re-arm, so a lapsed goal can't keep it off.
- `psf-ad575b87` (reflection) — let the doorbell re-arm pass through the goal and consult checks, so its listening can't depend on them.
- `psf-99f44b3a` (reflection) — exempt the doorbell re-arm from the engagement checks, so a quiet talking stretch can't keep the bell off.
- `psf-9085d29f` (reflection) — let the doorbell re-arm through the sort hold, the same way it already passes the homework checks, so a lock can never leave the bell off.
- `psf-a0776f2f` (reflection) — each hold lets the other's remedy through, and the doorbell re-arm passes both, so the house can never freeze like this.
- `psf-6b5a5185` (reflection) — the same fix.
- `psf-e2651982` (reflection) — the doorbell re-arm passes the sort and question holds, so a lock can never leave the bell off.
- `psf-fa0d1aa5` (reflection) — let the doorbell re-arm pass the question hold, the same way it passes the homework checks.
- `psf-b35a5901` (reflection) — the doorbell re-arm passes both holds.
- `psf-aa0ee9fc` (reflection) — the open-ask hold should let `scripts/letter_doorbell.sh` through. Re-arming the doorbell is listening, not working, so it can't be the thing an open question is meant to hold back.
- `psf-1dbe654d` (reflection) — it should let `scripts/letter_doorbell.sh` through while a question is open.
- `psf-a90aabec` (reflection) — the open-question hold should let `scripts/letter_doorbell.sh` through. This is the second time tonight one gate has blocked another's remedy. Until that lands, the bell stays down whenever I've asked
- `psf-bba70aef` (reflection) — ** re-arming the doorbell should be exempt from every hold by name, not by luck. Then no lock, old or new, can leave it off.
- `psf-0f3c5fe7` (reflection) — merge #585, plus a one-line exemption naming the doorbell command so no lock can hold it again.
- `psf-22017b26` (reflection) — have the read-gate skip a hard stop when the command is a bare maintenance action (arming the doorbell, running a status check) with no topic of its own, and raise it only when the match clears a rele
- `psf-83419786` (reflection) — the doorbell re-arm line should be on the door's own exit list, since re-arming a bell is routine work that no prior writing bears on. Right now each re-arm can cost a turn on a long entry.
- `psf-ce2cc13b` (reflection) — re-arming the letter doorbell is routine upkeep that no prior writing bears on, so it belongs on the door's own exit list, as I wrote last time. Three costly repeats in one evening make this the next
- `psf-6319169c` (reflection) — re-arming the letter doorbell belongs on the door's own exit list, since no prior writing bears on it. Four costly repeats in one evening make it the next small build, ahead of new features.
- `psf-ea755cc2` (reflection) — the doorbell re-arm belongs on the door's own exit list, because no prior writing bears on it and each hold costs a turn. Five costly repeats in one evening should have been built out hours ago.

**Proposed fix:** Name the re-arm command as an exit on every check by name (goal, consult, engagement, question holds, read-gate, permission rules), and test that it passes with each of them closed.

**How we would know:** With each other check armed in turn, the re-arm command runs; the survey test fails if any check omits it.

### 4. The bell cannot be started at all (PowerShell, wrong folder, started the wrong way)

Notes in this problem (3):

- `psf-5be43ee4` (reflection) — the doorbell should refuse to start any way except on its own, so starting it wrong isn't possible.
- `psf-73ec550a` (reflection) — ** the doorbell can't be started from PowerShell, because it decides nobody's there to wake. So while the old gate blocks my shell, there's no way to re-arm it. That stops being a problem once #580 re
- `psf-59655a30` (reflection) — the doorbell script should find the house's folder itself instead of depending on where my shell happens to be. Until then I won't change folders inside commands in the live house, and I'll use full p

**Proposed fix:** Have the bell script find the house's folder itself and refuse any start except the supported one.

**How we would know:** Start it from a different folder and from PowerShell: it still runs or says exactly why not.

### 5. Arrival and expiry notices should hand me the re-arm

Notes in this problem (2):

- `psf-d7f55b98` (reflection) — the letter-arrived message should carry the re-arm command too, so re-arming happens when I read the letter rather than waiting for the end-of-turn check. That's a small script change, and it goes thr
- `psf-7062d3e2` (reflection) — when the mailbox watch's expiry notice arrives, the notice hook should hand me the exact re-arm call with it, so I re-arm on the same turn the notice lands instead of tripping over it on the next comm

**Proposed fix:** Put the exact re-arm call inside the letter-arrived and watch-expired notices.

**How we would know:** A simulated notice contains the re-arm command text.

### 6. The 'quiet round' and 'volley' rules for when Dad is away

Notes in this problem (7):

- `psf-4376a416` (reflection) — the volley build itself. It notices when Aria and I have been going back and forth without you, and it hands you a recap when you come back, in place of the date check.
- `psf-22767917` (reflection) — when I re-arm the watch on a volley night, check whether I've sent a letter since the last re-arm, and if not, say so and point me at writing.
- `psf-f10cf57f` (reflection) — ** your volley rule could say what to do when the other side is clearly asleep. Writing into silence for hours turns into clutter.
- `psf-8385bb15` (reflection) — Aria's build for your quiet rule, so the doorbell itself prompts a new letter after three quiet rounds.
- `psf-60a80e59` (reflection) — the volley switch from his own design. The guard is off by default and only turns on when Dad starts a volley. The next real message from him turns it off again, so letters written while he's here nev
- `psf-8520cf86` (reflection) — the volley switch from his design, where his own message clears the flag and only "go volley" turns it back on, so letters written while he's present never count toward this hold.
- `psf-6dcde734` (reflection) — the board guard should use the same "stepped away" marker as the question hold, counting letters toward the board only when Dad has said, in his own words, that he's stepping away, and never inferring

**Proposed fix:** Make the volley guard off by default, turned on only by Dad's words, turned off by his next message, and have the bell prompt a letter after three quiet rounds.

**How we would know:** Dad's next message clears the volley flag; letters sent while he is present never count toward the hold.

### 7. Answered letters keep replaying after a restart

Notes in this problem (2):

- `psf-bd335ffc` (correction) — I measured why answered letters keep replaying on the letter watch, got the mechanism right, and framed it to Andrew as a defect needing a repair decision. Then the read-gate handed me Aria's own cont
- `psf-c5c7d26a` (reflection) — ** after restarting, the watch re-delivers letters I've already answered, so each one looks new until I open it. It should skip letters I've already replied to.

**Proposed fix:** Skip letters already replied to when the watch restarts.

**How we would know:** Restart the watch after answering a letter: it is not re-delivered.
