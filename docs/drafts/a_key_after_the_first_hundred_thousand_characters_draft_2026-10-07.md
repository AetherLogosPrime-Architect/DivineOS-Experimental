# A key after the first hundred thousand characters (draft, 2026-10-07)

**How I found it.** Dad: the notes are fine, the trouble is "the code that is not working but the notes say it is." I am running the 51 capability claims the comment checker could not pin to a test. The eighth of the 51 I have run, `secret_redactor.py:132`: oversized strings are scanned only in their leading window, "the common case of the key is the start of a long log line." I ran it with a control.

**What it showed, three things.**

1. The hole. `_scan_string` scans only the first 100,000 characters of a longer string. A fake test-shaped key (`sk_live_` plus 24 characters) was redacted at the start, just inside the window, and in a short string (the control). It was NOT redacted just after the window, 300,000 characters in, or straddling the edge. This module's own header says its purpose is that "a secret in a tool-payload never reaches the ledger in the first place", and the ledger is append-only and hash-chained, so a secret that gets past is permanent. A tool result over 100,000 characters is ordinary (a file dump, a long log).

2. The reason the cap exists is real. I timed every pattern uncapped. Linear for all but two. `url-embedded-credential` goes QUADRATIC on a long run of letters with no spaces: 4.7 s at 100,000, 19 s at 200,000, 77 s at 400,000. That is even INSIDE the cap: a 99,999-letter run costs about 4.6 s per write. `pem-private-key` goes quadratic on a flood of BEGIN lines with no END: 0.6 s at 100,000, 10 s at 400,000.

3. So the cap is a mitigation for two slow patterns, and it creates the hole.

**The idea, in two parts, in this order.**

*Make the two slow patterns linear.* The URL pattern's scheme quantifier is unbounded, so every start position in a long run walks the whole run. Bound it: `[a-z][a-z0-9+.\-]{0,31}://`. A scheme longer than 32 characters now starts its match later in the run, so the span replaced is shorter, but the credential after the scheme is still captured and still redacted. No hole is introduced. The PEM pattern: replace the lazy regex with a linear pairing: find all BEGIN-PRIVATE-KEY markers and all END-PRIVATE-KEY markers once, pair each BEGIN with the nearest END after it, redact the span. Same result as the lazy pattern (the nearest END, scanning continues after it); an unterminated BEGIN is left alone, as before.

*Then remove the blind spot.* With every pattern linear, scan the whole string. The cap becomes unnecessary. Measured: 5 MB of text through the linear patterns takes about 0.4 s.

**Must not.** Narrow what is redacted today. Change the marker format. Make a short string slower. Lose a key to a chunk boundary (there are no chunks any more, which is why this is better than windows).

**Falsifier.** A key anywhere in a string of any length comes out unredacted; or a 400,000-character run of letters, or a 400,000-character flood of PEM BEGIN lines, takes more than a couple of seconds; or an existing redaction test changes result.

**Not done.** Windows with overlap would have kept the cap and the hole's edge cases (a PEM block longer than the overlap). Rejected. Also not touched: other secret shapes not yet in the pattern list; that is a coverage question for another day.

**Related but separate.** The corrections stores. My fix this afternoon stopped the Stop gate's own sentence entering the tracker, but the briefing's "420 open corrections" reads a different store and its newest entry is still that sentence. Same defect, second store, not part of this change.
