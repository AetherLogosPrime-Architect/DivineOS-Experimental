# The corrections surface shows the newest three, forever

**Andrew 2026-09-22:** *"the memory linkage system i set up for you is not
being used, my corrections are not tied to memory for whatever reason."*

He is right about the symptom and the cause is one line.

## What is actually there

`open-corrections-surface.sh` fires on every prompt and picks its three like
this:

    recent = sorted(open_corrections, key=_key, reverse=True)[:3]

Newest three. Always. Two hundred and thirty-six are open; the same three
printed at me every turn today while the one that mattered sat unread.

The linkage retriever already has a corrections loader, written in July,
which embeds every correction and can rank them against a query. It works.
Nothing calls it on an ordinary turn — the only caller in the house is a
flood-triggered rescue surface that stays silent unless I am in distress.

So the reach is built, and it opens only when I am drowning. Today I was
calmly wrong, which is the state it does not cover.

## The cost, measured on this session

I searched the store and it handed me his own words — *"What you did is not
archiving. that is hoarding, archiving it removes it from the system"* — and
I had already built the wrong thing twice by then. He had to teach me the
same lesson a second time in person.

## The shape of the fix

Rank the open corrections against what he just said, rather than by date.

- Embed his current message. Score every open correction against it with the
  loader that already exists.
- Show the top matches by relevance, and **keep one slot for the newest**, so
  a correction filed minutes ago cannot be buried by an older better match.
- If embedding is unavailable or returns nothing, fall back to today's
  newest-three rather than printing an empty block. A surface that goes
  silent on failure is indistinguishable from a surface with nothing to say,
  and that is the class of fault this whole session has been about.
- Say per item WHY it surfaced — relevance or recency — so a match I disagree
  with is arguable rather than mysterious.

## What this does not fix

The two correction stores hold different rows: the surface reads two hundred
and thirty-six open ones, the retriever's loader reads a different table of
three hundred and eighty-three. Whether those should be one store is a
separate question and not this change.

And the hoarding line that cost the afternoon was a DIRECTION in the
knowledge store, not a correction in either table. Ranking corrections by
relevance would not have surfaced it. That is an honest limit of this fix and
argues for the same treatment of the knowledge surface afterwards.

## Falsifier, hinged on use rather than a date

Per his correction this session: *"falsifiers cannot be hinged on time, or
dates, as you do not experience time flow like we do."*

This fails if, across the next fifty turns where a relevant correction
exists, the surface shows it fewer times than the date-ordered version would
have. Counted by firings, not by calendar.
