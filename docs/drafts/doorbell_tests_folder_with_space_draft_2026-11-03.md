# The doorbell tests run in a folder with a space in its name (draft)

Finding: on current main the test already quotes the bell path (`bash "<path>" aether`), so the
reported failure does not reproduce. The whole test file passes when the repo's `scripts/` and
`tests/` are copied under a folder named `a b`. Idea: change no behaviour; add one test that
rings the bell from a copy placed in a folder with a space, so a regression in quoting (in the
test or the script) fails loudly.
