# One reader for voiced filings (draft, 2026-10-11)

**Idea.** Whether an audit filing is a remedy is decided by two readers of one line: a regex over the raw text decides whether to look at the actor, and the token parser decides whether the command is on the exit list. `audit "submit" ... --actor user` slips past the first (the quote hides the word) while the second sees `submit`, so a filing in Dad's voice passed with no pause. That is Aether's second hold on 621.

**Change.** Delete both regexes. Recognise a filing from the parsed chain links the remedy match already reads, read the actor from that link's own tokens, require exactly one actor that is a literal from the closed list (or a `claude-` variant), and fail toward the pause on anything else or any parse trouble.

**Proof.** A generated family quotes and splits every word of each filing command, with an environment prefix and an equals form of the actor: no variant naming the user actor may be a remedy, and the same variants naming a closed-list actor still are (a list that refused everything must not pass). It was red first, 44 failures, including Aether's case verbatim.

**Not in this change.** The loose prefix in the shell list; `ask-resolve` and `extract` on the python list.
