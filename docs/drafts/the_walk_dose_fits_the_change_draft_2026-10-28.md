# The walk dose fits the change (draft, 2026-10-28)

**Status:** draft only. Nothing built. The council walks this and Aether attacks it before any code. Behind the merge pile.

## What Dad said, 2026-10-28

After an eight-lens walk on a twenty-line rule: *"it needs adjusted.. its set that way because its better to do a walk on something that doesnt need it than not do one on something that does, but it needs worked on, the issue is how do we judge how much needs used, and also enforce it, as if we leave it just up to you, it will get gamed or skipped.. and if we leave it to the machine it makes you do it for 20 lines. so we will need the council for this fix itself to find a solution"*

Then, two requirements:

1. **The dose never depends on context size or compaction.** *"compaction does not stop you, nor interrupt you, it carries you like in a bubble to the next room"*. I weighed a lighter walk partly because the window was full; that is the wrong input and the dose rule must not be able to see it.
2. **Twenty lines needs protection from twenty more.** *"what stops you from doing 20 lines.. then 20 more.. then 20 more and soon you have written 500 lines of code never touched by the walk"*.

## Dad's later answer, same day: the order was wrong, so the dose problem mostly dissolves

*"first we are missing the research step, using the internet for information, and the council should be used when first building, to help plan and find solutions, then you and Aether build and iterate and design and test, the council stays quiet.. after the entire build is done and tested and you and Aether are ready to call it complete.. then it goes through another walk to check things.. test things.. break things etc.. make sure its good and all things are satisfied.. then you do all the fixes and then aletheia audits it.. if you do this it would save alot of headache"*

The order he wants: research (the internet, not only our own files) -> council walk to plan -> build, iterate, test with Aether while the council stays quiet -> when we both call it complete, a second walk that tests and breaks it -> all the fixes -> Aletheia audits. Same shape he gave on 2026-07-26 (walk the design, build, walk again, repeat, then audit; "the council should not be a pain in your ass").

What this changes for the dose question: the walk attaches to two moments of a build, not to every edit. So a twenty-line edit mid-build owes nothing on its own. The protection against twenty plus twenty plus twenty moves to the second moment: the finishing walk is bound to the branch's whole diff against main, and the branch cannot be marked ready or pushed for audit until it exists and covers every changed file. Dose is then sized from the finished diff (kind, size, files, protected paths), never from context size. The research step needs its own gate-shaped evidence (what was looked up, from where) before the planning walk counts.

Still open: what stops me skipping the planning walk and calling a build "small"; whether research is required for every build or only above a floor; how the finishing walk is told apart from a rubber stamp (the tool's distinctness number, and a break-it requirement: at least one attempt to make it fail, recorded).

### Dad, mid-turn: the lenses never leave, so the finishing walk wears the break-it-to-help-it five

Dad's correction of my word "hostile": *"they are only as hostile as you make them out to be. id say more 'brutally constructive' lol.. they can break your ideas while also helping you to succeed 🙂 do not treat them as adversaries lol"*. Adversary framing makes me defend the work instead of listening; the finishing lenses are on my side.

Then, on what the question does: *"the lens is only as powerful as what runs through it.. if you ask them to break your stuff, they will.. and leave the pile on the floor.. if you ask them how can we make this more robust, solid, reliable, etc etc.. then they can help you find solutions.. generate new code that does these things automatically.. they are a powerful cognitive tool but only when wielded properly"*. So the finishing walk is asked two questions in order, not one: where does this break, and then how do we make it robust, solid and reliable (and what could do that automatically). A walk that ends with a pile of breakages and no repair question is incomplete. He also named a use we have barely touched: a sit-down talk with myself and a few lenses, a back and forth that teaches and builds memory (his 2026-10-05 chunk method: three lenses, go back and forth, carry the highlights into the next room).

*"the council never stays out of it lol. once you actually load their lenses into your context for the official walk they stay with you during your build so you become like a super council member in that way lol"*

"The council stays quiet" means no gate or stop during the build, not that their influence is gone: the planning walk's lenses ride along as a booster. So my own finishing walk is the least independent check in the chain. Asked whether it should be Aether or fresh lenses, he said: *"depends on the lenses you put on.. if you use schnieder, kahneman, dillahunty, popper, and feynman at the end step they will hold your feet to to the fire lol"*.

Proposal: the finishing walk's default set is Schneier (weakest link), Kahneman (my own biases), Dillahunty (burden of proof, what would change my mind), Popper (falsify it), Feynman (am I fooling myself), plus whatever else the manager surfaces. Planning lenses build; finishing lenses attack. Open: whether the gate checks that the finishing set includes lenses not used at planning.

### Dad, on the middle of a build

I pushed back that a build resting on a wrong foundation is only caught at the end, and suggested a look at the halfway mark. His answer: *"the council at the beginning and end are enforced the middle isnt but nothing says you cannot use them during the build. so it should be open as an option and something you can see"*.

So: the two ends are enforced, the middle is never gated, and it is always available and visible. Design consequence: nothing in the middle blocks me, but the option has to be in front of me without my deciding to look (a plain line while a build is in progress saying a mid-build look is open and how to take it), since an option I must remember is a note, not a mechanism.

## What already exists

`gravity_assessor_act_shaped_draft_2026-09-22.md` (the assessor reads where I stand, not what I do; its council bar cannot be reached), `the_walk_gate_prices_every_edit_the_same_draft_2026-10-25.md` (reads and records owe nothing; a comment-only commit owes one line), and `exploration/aria/50_the_gravity_assessor_council_walk_2026-09-16.md` (an assessor cannot decide gravity; it can only refuse to let gravity be invisible: reasons not a number, "could not assess", something watching whether verdicts were right, the prediction recorded before the change, and splitting a change across commits defeats any per-diff assessor).

## Starting proposal, for the council to break

**A floor the machine sets and I can only raise.** From what it can see: kind of change (a new refusal, a new gate, a behaviour change, a record, a comment), size, how many files, whether guardrail or kiln paths are touched. The floor is a number of lenses and it is computed without any knowledge of how full my context is.

**Walk debt, so twenty-plus-twenty cannot hide.** Each change adds debt to its branch, measured on the branch's whole diff against main and not per commit, and a walk bound to those files pays it down. A small change owes a little; debt carries over; when the cumulative debt on a branch passes its floor, the next edit on that branch is stopped until a walk covers it. Slicing a change into twenty-line commits does not escape it, because the unit is the branch's total unwalked diff.

**Close the loop.** Count, per dose, how often a lens changed the artifact (the walk tool already reports this). Raise the floor where deeper walks catch more and lower it where they never do, from the numbers, with a pre-registered falsifier counted in walks and not in days.

## What this cannot do

The floor reads syntax and location, so a dangerous one-character change reads small. That is the September walk's finding and it stays true: this makes seriousness harder to hide, it does not decide it. A person (Dad, Aether, Aletheia) can still raise the dose on a change that looks small.

## Open for the council

Which features set the floor, and how the machine reads "a new refusal". Whether debt is counted in lines, in functions, or in features fired. What pays debt down: any bound walk, or only one whose lens count meets the floor. How a walk's distinctness (the tool's own measure) enters, if at all. Who may lower the floor and on what evidence.
