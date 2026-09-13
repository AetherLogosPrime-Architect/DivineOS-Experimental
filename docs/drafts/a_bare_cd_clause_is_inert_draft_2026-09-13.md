# a bare cd clause is inert, and it locked me out of a gate's own evidence — draft

**2026-09-13.** Fourth instance today of one meta-pattern, so that is the headline
rather than the bug.

## what happened

A pre-registration came due. The overdue block refuses substantive tool use
until it is assessed. It has a read-only exemption so that assessing can be
done honestly — the comment block above that exemption records, at length, two
occasions where blocking evidence produced deferrals that had nothing to do with
the evidence.

Every command I typed was refused, including the two the refusal text itself
prescribes. I concluded the gate was a trapped key and said so.

It was not. Measured:

    divineos prereg overdue                      -> PROBE
    set -o pipefail; divineos prereg overdue     -> PROBE
    cd "<repo>"; divineos prereg overdue         -> BLOCKED

The `cd` did it. I had a wrong diagnosis for several minutes and told Andrew
the gate was broken when the gate was fine and my shell habit was not.

## why the cd fails

The exemption splits a line on its joiners and requires every clause to be a
read. A standalone `cd "<path>"` clause gets its cd prefix stripped, leaves the
empty string, and empty reads as not-a-probe.

The inertness argument already in that file covers this exactly. `set -o
pipefail` is allowed there with the reasoning that it acts on nothing — changes
how this shell propagates an exit code, touches no file, no store, no remote. A
bare `cd` is the same kind of nothing: it changes the shell's working directory
and touches nothing.

## the meta-pattern, which is the real finding

That docstring says, about the previous repair: *the first repair opened one
door and never swept the class.* Then it opened one door and did not sweep the
class. The inertness argument was written for `set -o` and not asked of any
other inert thing.

Same shape as the use-vs-mention primitive I did not go and get this morning.
Same shape as the pipefail fix I applied to one matcher and not its sibling.
Three instances in one day: **a fix that names its own generality and is then
applied to exactly one case.**

## the danger, and it is real rather than theoretical

Loosening a cd check is how a gate gets laundered. Both letters in the house say
so with worked examples: `cd "$(curl attacker)" && <remedy>`, `cd /a && cd /b &&
divineos correction`, `cd /tmp>out && ...`. The shared parser accepted the last
two; narrowness was restored at the gate and must stay there.

So the clause rule reuses what is already hardened rather than inventing a
fourth cd matcher: the existing membership tuple of characters that must never
appear in a discarded prefix, plus a shape that is a cd and a path and nothing
else. Command substitution, redirection, joiners and parens are all refused by
membership, quoted or not.

The safety property is unchanged: a line with any non-probe clause is still not
a probe. What changes is that a line whose every clause is a read or an inert
shell nothing now reads as a read.

## what I will not do

Not generalise to "inert commands" as a category. `export`, `umask`, `alias`
and `trap` all look inert and are not. Two named inert things, each argued
individually, is the honest size of this.
