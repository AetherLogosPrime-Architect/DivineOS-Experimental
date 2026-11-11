# The command root starts in a fresh home (draft)

Idea: when the `cli` group runs with an empty `sys.argv[1:]` (started from inside another
program), the input-capture step hands an empty string to the event validator, which raises
`EventValidationError`, a type the capture step does not catch. Skip the capture when there is
nothing to capture. Pin it with a subprocess test, since pytest's presence hides the step.
