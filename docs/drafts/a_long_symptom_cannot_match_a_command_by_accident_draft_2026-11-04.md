# A long symptom cannot match a command by accident (draft, 2026-11-04)

**The idea.** The reach check surfaces prior art for a symptom I type. On 2026-11-04 I typed a long
sentence ("... before a tool call that changes something ...") and it surfaced `divineos changes`, a
command that lists what changed in the knowledge store. Dad: "if it doesnt fit make it stop showing
up". It was not a judgement call, it was the matcher.

**Why.** `prior_art.find_commands` squashes the symptom into one string with no spaces and asks
whether any command name of four or more letters appears inside it. A whole sentence is a long
string, so any command named with an ordinary word (changes, find, context, log) matches by
accident, and a command can match across the joins between words. Disposing `not_relevant` only
clears that one item; the next sentence with the same word surfaces it again.

**What this changes.** The "command name inside the term" direction applies only to a short term,
three words or fewer, which is a name being looked up. A long sentence matches commands only the
other way round (the term inside a command name), which a long sentence never satisfies. The
working-tree, loadout and commit axes are untouched and still read the whole sentence.

**What it cannot do.** A short symptom of one ordinary word ("changes") still matches the command
`changes`: that is a real name lookup. A command a long symptom truly names is no longer surfaced
by this axis; the other axes still search it.

**Falsifier.** A long symptom containing a command's name still surfaces that command; or a short
name lookup stops finding its command.

**Owed.** A walk, Aria's read, Aletheia's confirm, Dad's yes.
