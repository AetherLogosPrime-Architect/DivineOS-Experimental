# The order-question guard: build notes (draft, 2026-10-08)

Continues `a_reply_cannot_end_by_asking_dad_which_order_draft_2026-10-08.md`; prereg-c4888c81eca6 is filed and the walk was done, but a save in between landed the previous work item and the front door asked for the opening steps again, so they are repeated here.

Build, in this order: a module `order_question_check` with `find_order_question`, `names_why_order_matters`, `should_refuse` and `refusal_message`; a Stop surface registered in `hook_surfaces` beside the other refusing surfaces, in-process, no new hook script; a test file that holds the nine-times phrasings and today's real ones (refused), a real dependency (passes), ordinary questions (pass), and the surface end to end.

Controls to run before calling it done: the real phrasings from this session come back refused; the engine-before-chassis case passes; a question in an earlier paragraph does not trigger it; cutting the module away turns the tests red.

Found while doing this, for Aether: the doorman counts preparation done before a commit as spent by that commit, so reach, draft and walk done early for the NEXT piece must be redone after the save in between.
