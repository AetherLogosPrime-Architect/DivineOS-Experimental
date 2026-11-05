# Night-letter overwrite door (rough draft, 2026-11-03)

Two seats write into one shared file a night. The Write tool replaces the whole
file and says "updated" for it, so Aria's Write erased Aether's section.

Idea: a surface on the PreToolUse doorbell. Write to
`the-night-letter-to-andrew-YYYY-MM-DD.md` when it already exists is refused,
and the refusal names the two ways in: an Edit that appends under your own
`## From <seat>` heading, or a shell `cat >> file <<'EOF'` append. A Write to
one that does not exist yet (creation) stays allowed.

Shape: judgment in `core/night_letter_overwrite_check.py`, surface in
`hook_surfaces.py`, registered in the same change. No new settings.json entry:
the doorbell already matches Write, so the hook count does not move.
Cannot see: other tools that replace the file, aliases/symlinks, races.
