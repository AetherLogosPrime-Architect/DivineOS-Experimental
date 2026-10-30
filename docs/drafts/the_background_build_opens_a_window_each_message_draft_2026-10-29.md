# The background index build opens a console window on every message (draft, 2026-10-29)

Dad's report: a black window titled with the venv python path appears each time he sends a message; it was solved before and came back the night I restored his-words files from main.

Cause (evidenced by reading): start_background_build launches the index build with DETACHED_PROCESS. The venv python.exe is a launcher that starts the real python as a child; a detached parent has no console, so the child opens a fresh visible one. The surface line "a build is running in the background" shows it fires on messages while any passage is unindexed.

Fix: CREATE_NO_WINDOW instead (the house rule in windowless_launch_check). The child gets a hidden console and its own children inherit it. Keep CREATE_NEW_PROCESS_GROUP so it still outlives the prompt.

Guard: a test that reads the source and refuses DETACHED_PROCESS in this launch.
