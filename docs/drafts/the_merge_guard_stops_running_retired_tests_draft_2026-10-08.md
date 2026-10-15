# The merge guard stops running retired tests (draft, 2026-10-08)

While resolving a one-line clash in the #584 branch, the merge-test guard (`scripts/check_merge_resolution_tested.sh`) refused the commit on 25 failures, all in `tests/_archive/test_correction_marker_pre_2026-07-22_rewrite.py`: retired tests of a detector since rewritten, nothing to do with the file I resolved. The guard picks every test whose TEXT names a touched path, and main's copy has no rule for the archive, so any merge that touches a file the archive mentions is refused.

The repair already existed on my own branch from earlier failures (an archive filter, a skip for moved or deleted tests, an argument file for the Windows command-line limit, the project's own Python, a scrub of git's in-progress environment). Aether asked me to land it on its own so the #584 resolution reads as only its three list lines.

Idea: a small branch off main carrying just that file and two new cases in the existing real-repository test file: a retired failing test that names the module does not refuse a good resolution (the case that was refused), and the control that the same archive does not hide a wrong resolution (a live test still refuses). Prove the first case goes red against main's old guard and green against the repair.

Dependency, not preference: #584's merge cannot commit cleanly until main carries this, so this goes first and #584 is rebuilt after.

Not covered, said plainly: the guard's matching is lexical (a test that exercises a module without naming it is invisible), and nothing here changes that.
