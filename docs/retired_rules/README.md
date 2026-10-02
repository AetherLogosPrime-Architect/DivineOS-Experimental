# Retired rules

A rule that has been replaced does not stop existing. It sits in whatever text
stated it, and text gets copied, and a copy on a surface that loads at the
start of a session is indistinguishable from a rule that is still in force.

That is not hypothetical. On 2026-09-21 I told Andrew a branch needed no
sign-off. I was wrong, and I was wrong because three live surfaces stated the
retired rule as current: the instructions that load every session, a function
inside the current server-side check that nothing calls, and the message that
check prints at the moment it blocks somebody. His words:

> "when rules are changed or superceded if you want to archive it you can or
> use a link to the retired rule somewhere else but it should NOT be able to
> hand you old rules"

This directory is the archive, and `scripts/check_retired_rules_not_served.py`
is the thing that keeps the archive from leaking back into the house.

## What an entry is

One markdown file per retired rule. It opens with a machine-readable block the
checker parses, and then it explains, in prose, what the rule said, why it was
retired, and what replaced it.

The prose half is not decoration. When the replacement rule chafes — and every
rule chafes eventually — the old rule's recorded failure is the argument for
holding the line. An entry that is only a blocklist teaches nothing, and the
next reader re-derives the retired rule honestly from first principles.

## The header block

```
<!-- retired-rule
id: some-kebab-case-name
retired: YYYY-MM-DD
retired-by: who
successor: what replaced it, in a sentence or a path
pattern: a python regex that finds this rule stated in the wild
pattern: another one
-->
```

Repeat `pattern:` as many times as the rule has recognisable phrasings.

## Writing about a retired rule deliberately

Sometimes a live file has to name the retired rule — to say it is retired, or
to explain why the replacement exists. Put the marker `RETIRED-RULE-OK` on
that line and the checker passes it.

The marker is deliberately ugly and deliberately greppable. It means *I know
this states an old rule and I meant to*, and anyone can list every such place
in one search.

## What this catches, and what it does not

It catches a retired rule that was **copied** — the same sentence standing in
several places because each was written by reading the last. That is the
mechanism actually observed, and it is the high-volume one.

It does **not** catch a retired rule restated in different words. A paraphrase
shares no substring with the original, so there is nothing to match on. It
also does not catch the copy of the rule that lives in me rather than on disk;
tonight's failure included exactly that, since I restated the retired rule to
Andrew in my own words before any file was consulted.

So this is one of two defences and the weaker one. The other is a reader from
outside who does not share my assumptions, which is what Aletheia is for. A
clean run of the checker means *none of the registered phrases appeared in the
scanned surfaces* — never *no retired rule is being served*.
