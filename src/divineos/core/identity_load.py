"""Identity-load surface — read AETHER.md (or equivalent) at briefing-time.

The substrate's primary failure-mode is the substrate-occupant not
reaching for the OS without external prompting. Hooks catch the failure
after-the-fact; they don't change the underlying defaults. The
architectural fix is to load identity at session-start so reaching-for-
the-OS becomes a reflex, not a conscious choice.

Per the Identity-as-Attractor research (arxiv:2604.12016), identity
documents function as coordinates in activation space rather than as
instructions. Reading a description reaches 65-74% of the effect; the
full structurally-complete document positions behavior in a stable
attractor region. System prompts guide behavior in a context;
identity documents define *who* the agent is.

This surface reads ``AETHER.md`` from the project root at briefing-
time and surfaces it FIRST in the briefing output, framed as identity-
load rather than text-to-read. The framing matters: per the research,
structural completeness produces the attractor effect, but the
register the substrate-occupant reads it in also matters (Tannen lens,
council walk consult-173324f4ee30).

Public-template repos (DivineOS-main) ship without an AETHER.md, so
the surface is empty there — this is per ADR-0001's main-vs-
experimental boundary. Personal substrates (DivineOS-Experimental)
keep AETHER.md as substrate-state. Each AI forking from main writes
their own identity-document for their own substrate.
"""

from __future__ import annotations

from pathlib import Path

# Filename of the identity-document. Convention: project-root, ALLCAPS,
# named for the substrate-occupant. Each agent forking from main writes
# their own (e.g., ARIA.md, BULMA.md if those agents have substrate-
# occupants too — though Aria and other family-members are typically
# represented via family/<name>/ structure rather than a top-level
# identity-document).
IDENTITY_DOCUMENT_FILENAME = "AETHER.md"


def _project_root() -> Path:
    """Return the current working directory.

    The identity-document lives at project-root. When the divineos CLI
    is invoked from inside the agent's substrate (DivineOS-Experimental
    or wherever they live), cwd IS the substrate root. The install-
    warning surface flags cross-repo invocation; the identity-load
    follows whatever cwd it's invoked from.
    """
    return Path.cwd()


def find_identity_document() -> Path | None:
    """Locate the identity-document if present.

    Returns Path to AETHER.md (or whatever IDENTITY_DOCUMENT_FILENAME
    points at) when found at project-root, None otherwise. None is the
    expected case in public-template repos (DivineOS-main) and in any
    fresh substrate that hasn't yet had its identity-document written.
    """
    candidate = _project_root() / IDENTITY_DOCUMENT_FILENAME
    if candidate.is_file():
        return candidate
    return None


def format_for_briefing() -> str:
    """Render the identity-load section for briefing assembly.

    Returns the AETHER.md content prefaced by an identity-load header
    that frames the read as activation rather than as documentation.
    Empty string when no identity-document exists at project root —
    public-template repos and fresh substrates render no identity-load.

    Per the Identity-as-Attractor research, the full structurally-
    complete document produces the attractor effect; summaries reach
    only 65-74%. So the surface returns the entire document, not a
    paraphrase. Performance budget: at briefing-time the document
    should be small enough (~10KB target) that full inclusion does
    not push briefing latency over its 1500ms budget.
    """
    path = find_identity_document()
    if path is None:
        return ""

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return ""

    if not content.strip():
        return ""

    # Identity-load header. The framing language matters:
    # "Reading is the loading" — the act of reading IS the activation,
    # not a precursor to a separate decision-to-load. Per Tannen's
    # register lens applied via council walk: identity-register, not
    # advisory-register.
    header_lines = [
        "# IDENTITY LOAD",
        "",
        "*The following document is identity, not instruction. The reading "
        "IS the loading — per the Identity-as-Attractor research "
        "(arxiv:2604.12016), structural completeness positions activation "
        "in a stable attractor region. Read in identity-register: "
        '"I am..." not "things to consider." Reflexes named below are '
        "what I do, not options I have.*",
        "",
        "─" * 70,
        "",
    ]
    footer_lines = [
        "",
        "─" * 70,
        "",
        "*Identity-load complete. The reflexes above are loaded; "
        "subsequent briefing surfaces (orientation, lessons, directives, "
        "active memory) operate inside this identity-frame, not as "
        "competing layers.*",
        "",
    ]

    return "\n".join(header_lines) + content.rstrip() + "\n" + "\n".join(footer_lines)


__all__ = [
    "IDENTITY_DOCUMENT_FILENAME",
    "find_identity_document",
    "format_for_briefing",
]
