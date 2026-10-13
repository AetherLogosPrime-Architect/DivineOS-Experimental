# What the branch board gets wrong — found by using it, not by reading it

Kept as a running note during the sort rather than fixed mid-sweep. Changing
the tool halfway through gives two different answers about one pile and leaves
nobody able to say which rows came from which version.

**Scale, measured:** 134 local branches against the trunk. Andrew sees seventy,
which is presumably what reached the server. The largest pile is fifty-seven
branches carrying code and writing together — unreviewable as they stand,
because a review request against one asks the auditor to read letters as
patches.

---

## Three misreads so far, and they are one fault

Every one of them is the board answering a question about the CONTAINER when
the question was about the CONTENTS. That is the same fault I fixed two weeks
ago in the lens-count check, in a neighbouring file, and did not carry across.

### 1. Code in a letters folder counted as a letter

`aria/pr-letter-provenance` was filed under *writing branch with a review
request wrongly open on it.* It is nine files of hooks, scripts, tests and
source. One file — `family/ear_watch.py` — is a Python program that lives in
the family directory because that is where the letter machinery lives.

The classifier decides what is writing by path prefix, so a program in a
letters folder is a letter.

**Cost:** a branch of real code has been sitting in the pile marked *never send
this for review; it is read, not diffed.* The pile label is an instruction not
to do the one thing that branch needs.

**Fix, when the sweep is done:** classify by extension as well as prefix.
Anything a lens can grip — source, tests, scripts, hooks — is code wherever it
sits.

### 2. A live branch flagged as superseded because of its name

`fix/a-file-already-gone-is-not-a-file-stuck-clean` landed in *maybe
superseded*. It is the branch I am committing to right now. The trigger is the
trailing word in the name.

The tool is behaving as documented — it says in its own docstring that this
pile is a name-shape guess and every row needs a human look — so this is the
guard working rather than failing. Noted because the rebuild convention
guarantees this pile will always contain live work, which makes the pile
dangerous to anyone who trusts labels.

### 3. The dangerous one: a keep-marker inside the delete pile

`aletheia/home-do-not-delete` is filed under *nothing against the trunk; close
or delete after a look.*

The branch's own name is a warning not to do the thing the pile label
suggests. Nothing was lost — the tool deletes nothing and says so loudly, and
the destructive path in this repository requires a justification naming the
exact target — but three guards held for a row that should never have been in
that pile at all.

**The deeper error is the label.** Zero files and zero commits against the
trunk does not mean *empty of purpose*. It can mean the branch IS the purpose:
an anchor, a pointer, a marker someone deliberately left standing. The pile
name asserts a verdict the measurement cannot support.

**Fix:** a branch carrying a keep-marker in its name never enters a
close-or-delete pile, and the pile is renamed to what was actually measured —
*nothing against the trunk* — with what to do about it left open.

---

## The pattern worth carrying

Two of the board's three heuristics read the branch NAME, and the third reads
the FOLDER. None of them opens anything. That was a defensible trade when the
board was a first pass over a hundred-odd rows, and it is the reason every
misreading above shares one shape.

It also means the board's real product is a shortened looking-list, exactly as
its docstring claims, and any sentence that treats a pile as a verdict is
reading it wrong — including mine, when I reported the writing-branch count
without opening one.
