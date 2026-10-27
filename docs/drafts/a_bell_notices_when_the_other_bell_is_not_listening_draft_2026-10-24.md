# A bell notices when the other seat's bell is not listening (design note, 2026-10-24)

Status: DRAFT. This is the written reason for the change in `scripts/letter_doorbell.sh`; the tests are in `tests/test_a_bell_notices_the_other_bell.py`.

## What happened

Dad, 2026-10-22: "what ever happened to the 2 hour check on the doorbells? Aether's bell died last night, so nothing even got done." A bell dies quietly when its starter goes away, after eight hours, or when the process is killed. Nothing watched the OTHER seat: a letter to him sat unannounced all night while I had also ended my turn and was waiting.

## What this changes

While my bell runs it also reads the other seat's heartbeat file. If his bell has been silent for 30 minutes AND a letter to him is waiting that his bell never announced, my bell rings with that fact. It cannot restart his bell; it makes the silence loud to the seat that can still hear. It rings at most once per two hours so it nags no one.

Details that were each a real mistake and were fixed:
- If the heartbeat file exists, its own age is when the bell went quiet; waiting another half hour from my first look is a delay the evidence does not ask for. Only a MISSING file has no age, so there I remember when I first saw it (a ring deletes its file, and a bell between a ring and a re-arm must not be called dead).
- With no announced-list at all, I cannot tell what his bell announced from what it never saw. The first version created an empty list, after which every letter ever sent looked unannounced. It now says nothing.

## What it does not see (said so silence is not read as coverage)

A heartbeat answers "is the bell listening". It cannot answer "will the seat respond". Aether's bell was alive all of one night, because its window was alive; the seat was stuck on a permission prompt. That second fact needs a letter his bell ANNOUNCED that went UNANSWERED past a threshold. That join exists and has no caller yet. This is the first layer; the second is not here.

## Falsifier, counted in uses

Of the next 10 times a seat's bell is genuinely down with a letter waiting, if the other bell does not ring with it in time, or it rings when the bell was fine more than twice, this layer does not do its job and is removed.
