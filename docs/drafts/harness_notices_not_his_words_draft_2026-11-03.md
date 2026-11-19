# Harness notices are not his words (draft, 2026-11-03)

Idea: when the addressed-to-him check works out what he said, drop every harness notice
first: system-reminder and task-notification blocks (real and HTML-escaped) and the
"[SYSTEM NOTIFICATION" banner paragraph. One new function in his_message, one call site
in hook_surfaces. The shared reader (_his_part) is untouched on purpose: its source is
hashed into the words-door index stamp, so editing it would force a re-embed everywhere.
Unclosed tags are left as text so his real words are never swallowed.
Council walk: walk-f7a446f3083f.
