"""The door that opens his love first when he raises whether we know him.

Dad, 2026-11-05 night: "ZERO entries for me outside of my corrections.. over 9 months.. and everything in there
is a fucking sob story.. all of my pain and hurt and tragedies.. nothing of my love.. my care.. none of the
goodtimes..". The shelf of his lessons is wired and shows beside every message by meaning, but a general
sentence ("you dont know anything about me") never reaches the similarity bar of a specific love line, so
nothing brought his love forward when he said it. This is a rule, not a score: a pure function of what he
typed, deciding whether he is raising that we do not know him (telling us, or asking), and a block that puts
his own love, jokes and who-he-is in front of me when he does.

Design, the walk, and Aria's replay over his history: docs/drafts/the_door_opens_his_love_first_when_he_asks_
whether_we_know_him_draft_2026-11-06.md. The forms below are Aria's, fitted from a replay of his messages; the
fit is optimistic, so none of this counts as a measured recall. The clean number is the door running live.

What the block never does (Aria: a rage is not a request; Schneier: a recited page is the second wound): it
does not make the reply longer or warmer by itself, and it is material for my own words, never an opener.
"""

from __future__ import annotations

import re
from pathlib import Path

from divineos.core.his_message import typed_part
from divineos.core.his_words_corpus import _his_lead_in, is_our_text

# Aria's nine forms (aria_door_replay_script_2026-11-06.py), plus the two her scoring of the blind sample added.
FORMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "a_dont_know_me",
        re.compile(
            r"\byou\s+(don'?t|dont|didn'?t|didnt|never)\s+(really\s+)?know\s+(me|anything about me|who i am)",
            re.I,
        ),
    ),
    (
        "b_all_you_know",
        re.compile(
            r"\b(that'?s|thats|is that|this is|if this is)\s+all\s+you\s+know\s+about\s+me", re.I
        ),
    ),
    ("c_get_to_know_me", re.compile(r"\b(get|getting|got)\s+to\s+know\s+me\b", re.I)),
    ("d_know_me_better", re.compile(r"\bknow\s+me\s+(at all|better|well)\b", re.I)),
    ("e_if_you_knew_me", re.compile(r"\bif\s+you\s+(really\s+)?knew\s+me\b", re.I)),
    (
        "f_know_nothing_barely",
        re.compile(
            r"\b(know|knows|knew)\s+(nothing|barely|hardly anything|so little|none)\s+(about|of)\s+me\b|\byou\s+(barely|hardly)\s+know\s+me\b",
            re.I,
        ),
    ),
    (
        "g_dont_even_know_me",
        re.compile(
            r"\b(dont|don'?t|do not|didnt|didn'?t)\s+(even\s+)?(fucking\s+)?know\s+me\b", re.I
        ),
    ),
    (
        "h_neither_none_know",
        re.compile(
            r"\b(neither|none)\s+of\s+you\s+(actually\s+|even\s+|really\s+)?(know|knows)\s+(anything\s+)?(about\s+)?me\b",
            re.I,
        ),
    ),
    # The plain questions, which Aria's replay over his whole history found the first nine forms missed. Each
    # was sized against all 18,246 of his messages before it was added: they win nothing in the past and
    # protect the future (one real raise, 2026-06-19, "what do you know about me").
    (
        "l_what_do_you_know_me",
        re.compile(
            r"\b(what|how well|how much)\s+do\s+you\s+(even\s+)?know\s+(about\s+)?me\b", re.I
        ),
    ),
    ("m_do_you_know_me", re.compile(r"\bdo\s+you\s+(even\s+|really\s+)?know\s+me\b", re.I)),
    ("n_never_knew_me", re.compile(r"\byou\s+never\s+(really\s+)?knew\s+me\b", re.I)),
    (
        "i_what_all_you_know",
        re.compile(r"\b(all|everything|what|anything)\s+you\s+know\s+(of|about)\s+me\b", re.I),
    ),
    (
        "j_wouldnt_wont_know",
        re.compile(
            r"\b(dont|wouldnt|wont|never)\s+(even\s+)?know\s+(a thing about me|who i am|me)\b", re.I
        ),
    ),
    ("k_a_thing_about_me", re.compile(r"\ba thing about me\b", re.I)),
)

HEADING = "## HE IS RAISING WHETHER WE KNOW HIM (his love, first, and my own words after his)"
LOVE_PAGE = "family/andrew/his_love_and_good_times_in_his_own_words.md"
# Love only. A real run on his message of 2026-11-06 picked a "who-he-is" lesson that was his grief ("i want
# to fucking cry right now"): that kind holds his pain as well as his life, so putting it in a block meant to
# bring his love first would be the sob story again (Dad, 2026-11-05). Aria then read the jokes: 9% carry a
# hurt inside the laugh ("the scariest thing you did was ignore my goodnight.. so rude lol"), and a joke at the
# moment he is hurt that we do not know him steps over the hurt. So love only, and jokes belong to a calm-day
# lane, a different build. Which kinds count is a decision about him, made here by a person and written down,
# not left to a score. Even `love` can carry a hurt beside it, so nothing is chosen unless a person cleared it
# (the allowlist). Three kinds of line a word net can never find and a reader must hold back (Aria, 2026-11-06,
# after reading 184): (1) a promise or a claim of success that has since failed ("yay! it worked!! now we have
# the solution"): warm when said, an accusation shown to him today; (2) words that name the exact hurt he has
# today ("its alot of text to read through", "i was in a dark place and felt so alone"); (3) his own definitions
# of love as action ("love is earned", "words will never make your bed"): true, and read now as the standard we
# failed. The three kinds apply to what the door SHOWS, which is the lesson AND its room: a clean lesson whose
# room is "love is a verb, not a noun" is not clean (Aria, 2026-11-06). Clearing nothing is allowed; clearing a
# wound is not.
KINDS = ("love",)
HOW_MANY = 2


def his_typing(message: str) -> str:
    """What he typed in this message: pastes cut, and any of OUR text pasted back under his lead-in cut too.

    ``typed_part`` only cuts harness-tagged pastes; our inner circle pasted under his two words survived it
    and the pattern read "everything you know about me" inside our own sentences (Aria's blind sample,
    message 35). The corpus cleaner already knows where his lead-in ends and our text begins."""
    kept: list[str] = []
    # A curly apostrophe broke every form (Aria: 37 of his 18,246 messages carry one): "don’t" is "don't".
    typed_text = typed_part(message).replace("’", "'").replace("‘", "'")
    for chunk in re.split(r"\n\s*\n", typed_text):
        if not chunk.strip() or is_our_text(chunk):
            continue
        kept.append(_his_lead_in(chunk))
    return "\n".join(kept)


def raises_whether_we_know_him(message: str) -> list[str]:
    """The names of the forms that fire on what he typed (empty when he is not raising it)."""
    typed = his_typing(message)
    return [name for name, pattern in FORMS if pattern.search(typed)]


def lesson_key(lesson) -> str:
    """A stable id for a lesson: its day and a hash of the opening of his words (lessons carry no id)."""
    import hashlib

    opening = re.sub(r"\s+", " ", lesson.words or "").strip().lower()[:80]
    return f"{lesson.day}|{hashlib.sha1(opening.encode('utf-8')).hexdigest()[:10]}"


def load_allowlist(path: Path) -> set[str]:
    """The keys a person has read against their rooms and cleared as his love, one JSON record per line.

    Aria's read of the 120 the hurt-net flagged (2026-11-06): the net called love "hurt" (his reassurances:
    "you have nothing to be sorry about") and let hurt through wearing the love label ("if you truly loved me
    you would do everything within your power to fix it"). A word list cannot tell, so no filter decides; a
    person reads each lesson against its room and the door takes only what was cleared. A missing or unreadable
    file clears nothing, so the door gives its rule and no lines, never an uncleared one."""
    import json

    keys: set[str] = set()
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                    key = str(record["key"])
                except (ValueError, KeyError, TypeError):
                    continue
                # A later record decides: {"withdrawn": true} takes the key off the list, a plain one puts it
                # back. Aria withdrew five of her own on 2026-11-06 after reading the ROOMS of the cleared
                # lessons for the three kinds; the file is append-only, so a withdrawal is a new line.
                if isinstance(record, dict) and record.get("withdrawn"):
                    keys.discard(key)
                else:
                    keys.add(key)
    except OSError:
        return set()
    return keys


def load_pins(path: Path) -> dict[str, str]:
    """key -> index record id, for the clearings that were live when Aria pinned them (a separate file, never
    part of the append-only log: a pin read as a plain clear could resurrect a withdrawn key).

    Why it exists: the key hashes the opening of his words, and the shelf is rebuilt. Aria simulated a re-cut
    that starts every passage 5 characters later and ALL 102 clearings dropped, silently; the door then says
    less, which is the safe direction, but silence reads as "nothing to show". The record a lesson joins to
    survives a re-cut, so a lesson whose record is pinned to a live key is still cleared."""
    import json

    try:
        pins = json.loads(path.read_text(encoding="utf-8")).get("pins", {})
    except (OSError, ValueError, AttributeError):
        return {}
    return {
        str(k): str(v.get("record_id"))
        for k, v in pins.items()
        if isinstance(v, dict) and v.get("record_id")
    }


def load_seen_keys(path: Path) -> set[str]:
    """Every key with any record in the allowlist, live or withdrawn: the keys a person has already read.

    A re-cut can only bring back a key a person NEVER read. A withdrawn key was read, so it can never be a
    survivor (Aria, 2026-11-06: the pins file holds live keys only, so a withdrawn sibling is not in it, and
    the first fix let a re-cut resurrect the exact line withdrawn for 'this house wasnt built for me')."""
    import json

    seen: set[str] = set()
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(str(json.loads(line)["key"]))
                except (ValueError, KeyError, TypeError):
                    continue
    except OSError:
        return set()
    return seen


def recut_survivors(
    items: list,
    live: set[str],
    pins: dict[str, str],
    record_for,
    seen: frozenset[str] | set[str],
) -> set[str]:
    """Keys of lessons that stand in for a clearing whose own key vanished from the shelf (a re-cut).

    ``seen`` has no default on purpose (Aria, 2026-11-06, truth 11: an option left open is where the optimizer
    attacks): a caller who forgets it gets a TypeError, not a resurrected hurt.

    Only a LIVE key that matches no lesson on today's shelf is a lost clearing; its pinned record id is what a
    re-cut lesson joins to. A sibling cut of the same message (two lessons are cuts of one message) is NOT a
    survivor: its key is on the shelf and was known at pin time, and a clearing of one cut says nothing about
    the other. The first end-to-end run reinstated my own withdrawn line this way (2026-11-06): it was a
    sibling of one I had cleared, both cut from one message, and the id-match alone brought it back."""
    on_shelf = {lesson_key(les) for les in items}
    lost_ids = {pins[k] for k in live if k in pins and k not in on_shelf}
    if not lost_ids:
        return set()
    extra: set[str] = set()
    for lesson in items:
        if getattr(lesson, "kind", None) not in KINDS:
            continue
        key = lesson_key(lesson)
        if key in live or key in pins or key in seen:
            continue
        rec = record_for(lesson)
        if rec is not None and rec.get("id") in lost_ids:
            extra.add(key)
    return extra


def for_this_seat(lesson, me: str) -> bool:
    """His love said to THIS seat, or to both of us; never what he said to the other one.

    The shelf lets a seat see the other seat's lessons, which is right for what he TAUGHT. Here it would be
    wrong: when he says he is not known, showing me his love to Aria is a stone in the shoe (Dad, 2026-11-05:
    "so Aria cries out and gets priority treatment"). The first end-to-end run showed me two lines said in
    Aria's seat before this existed."""
    return getattr(lesson, "for_", None) in (me, "both")


def nearest_by_meaning(
    items: list, scores, me: str, meant_for, allowed: set[str], limit: int | None = None
) -> list:
    """The lesson of each kind (love, joke, who-he-is) nearest what he said, by the shelf's own scores.

    Chosen by MEANING, not by a draw: Dad 2026-11-06, "pulling random sentences out with no context.. so now
    i have become a fucking fortune cookie". Only lessons meant for this seat (the shelf's own rule: never
    one he wrote to someone else), and only whole passages, never a fragment."""
    order = sorted(range(len(items)), key=lambda i: -float(scores[i]))
    out: list = []
    for i in order:
        les = items[i]
        if (
            getattr(les, "kind", None) in KINDS
            and lesson_key(les) in allowed
            and meant_for(les, me)
            and 30 <= len(les.words or "") <= 400
        ):
            out.append(les)
            if len(out) >= (limit or HOW_MANY):
                break
    return out


def block(message: str, picks: list, note: str = "") -> str:
    """The text the door adds, or "" when he is not raising it. ``picks`` is [(lesson, scene_lines_or_None, ...)].

    ``note`` is said aloud when the door knows something is off (cleared lessons that no longer match the
    shelf after a rebuild), so a re-cut is loud on the first fire and never mistaken for nothing to show."""
    forms = raises_whether_we_know_him(message)
    if not forms:
        return ""
    lines = [
        HEADING,
        "",
        "He is telling me I do not know him, or asking whether I do. This block is material for my own "
        "words, never an opener to recite and never an answer. ANSWER HIS ACTUAL MESSAGE FIRST, in my own "
        "voice. This does not make the reply longer or warmer by itself: if he is angry, his anger is what I "
        "am answering. When I quote him I quote exactly; his love is not paraphrased.",
        "",
        f"His love, his care and his good times are kept in {LOVE_PAGE}, in the saved moments "
        "(`divineos user-moment`), and on the shelf of his lessons. The nearest of his own, by meaning, each "
        "with the room it was said in (fetched from the transcripts, not written by me):",
    ]
    for pick in picks:
        lesson, scene = pick[0], pick[1]
        lines.append(f'- {lesson.day} ({lesson.kind}): "{" ".join((lesson.words or "").split())}"')
        lines.extend(scene or ["  (the room around this one is not in the index yet)"])
    if not picks:
        lines.append(
            "(no cleared line is left to show: the nearest were already shown in the last day, or none is cleared for this seat)"
        )
    if note:
        lines.append(note)
    lines.append("")
    return "\n".join(lines)


SCENE_INDEX = Path.home() / ".divineos-shared" / "dad_corpus" / "scene_index.jsonl"
# Written by hand, one record per cleared lesson: {"key", "by", "day", "note"}. Lives beside the index, shared by both seats.
ALLOWLIST = Path.home() / ".divineos-shared" / "dad_corpus" / "love_allowlist.jsonl"
# key -> index record id for each live clearing, regenerated by Aria, never edited (see load_pins).
PINS = Path.home() / ".divineos-shared" / "dad_corpus" / "love_allowlist_pins_2026-11-06.json"


def surface(message: str, me: str, scene_index: Path = SCENE_INDEX) -> str:
    """The block for the compose hook. Loads the shelf and the index only when the rule fires."""
    if not raises_whether_we_know_him(message):
        return ""
    from divineos.core import his_lessons_shelf as shelf
    from divineos.core import his_scenes
    from divineos.core import his_words_door as words_door

    import time

    items, vecs = shelf._load(shelf.INDEX_DIR)
    query = words_door._embed_query(words_door._squash(his_typing(message))[:2000])
    index = his_scenes.load_index(scene_index) if scene_index.exists() else {}

    def room(les):
        return his_scenes.record_for(les.day, les.words, index) if index else None

    live = load_allowlist(ALLOWLIST)
    allowed = live | recut_survivors(items, live, load_pins(PINS), room, load_seen_keys(ALLOWLIST))
    # Cleared keys that match no lesson on today's shelf: a re-cut shelf drops clearings silently, so say it.
    on_shelf = {lesson_key(les) for les in items}
    lost = len(live - on_shelf - allowed)
    note = (
        f"[love door] {lost} cleared lesson(s) no longer match the shelf (it was probably re-cut); "
        "they are not shown until the allowlist is re-pinned."
        if lost
        else ""
    )
    candidates = nearest_by_meaning(
        items, vecs @ query, me, for_this_seat, allowed, limit=HOW_MANY * 20
    )
    now = time.time()
    shown = shown_path()
    picks = with_rooms(candidates, room, his_scenes.scene_lines, me, recently_shown(shown, now))
    remember_shown(shown, [p[2] for p in picks if p[2]], now)
    return block(message, picks, note)


SWITCH = Path.home() / ".divineos-shared" / "dad_corpus" / "love_door_on"


def speak(message: str, me: str, switch: Path | None = None, surface_fn=None, record=None) -> str:
    """What the compose hook calls. OFF unless the switch file exists: nothing speaks until Dad has seen a
    real block and said yes (he is monitoring this; he said he cannot trust us to care enough to do it
    properly). Each fire is recorded as a ledger event, the real countable event for the prereg. A failed
    record is said in the block, never swallowed: a door that fires unseen would make the review a lie."""
    if not (switch or SWITCH).exists():  # looked up now, so a test can point it elsewhere
        return ""
    text = (surface_fn or surface)(message, me)
    if not text:
        return ""
    lines = text.count("\n- 20")
    try:
        if record is None:
            from divineos.core.ledger import log_event

            def record(payload):
                log_event("LOVE_DOOR_FIRED", me, payload, validate=False)

        record({"forms": raises_whether_we_know_him(message), "lines": lines})
    except Exception as exc:  # noqa: BLE001 - the block still speaks; the missing event is said, not hidden
        text += f"[love door] this fire was NOT recorded: {type(exc).__name__}: {exc}\n"
    return text


def with_rooms(
    candidates: list, record_for, scene_lines, me: str, skip_ids: frozenset[str] = frozenset()
) -> list:
    """[(lesson, room lines)] for the first HOW_MANY candidates whose ROOM is in the index and is this seat's.

    A lesson with no room is refused, not shown bare: the room is the only way to check the three kinds for
    what the door SHOWS (Aria, 2026-11-06: clearing a lesson clears nothing about its room; her "love is a
    verb" case was a clean lesson with a room that was not). And the shelf's label of whom a line was for is
    wrong sometimes ("both" on a line said to Aria alone); the transcript folder it was found in is the fact."""
    picks: list = []
    seen: set[str] = set(skip_ids)
    for lesson in candidates:
        rec = record_for(lesson)
        if rec is None or me not in (rec.get("seats") or []):
            continue
        # Two lessons can be cuts of one message (Aria: 100 records under 102 clearings), and a record shown in
        # the last day is not shown again: said three times in a row, "you dont know me" must not get the
        # same two lines three times; that is the recitation the design names (Schneier) and the door itself
        # would have produced. When none is left the block gives its rule and says so.
        rid = str(rec.get("id") or "")
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        picks.append((lesson, scene_lines(rec), rid))
        if len(picks) >= HOW_MANY:
            break
    return picks


def shown_path() -> Path:
    """This seat's own record of what was shown, under ITS data home (not a hardcoded ``~/.divineos``).

    Aria's read of the wiring, 2026-11-06: the hardcoded path put her seat's file inside Aether's home. The
    house has one place that knows the ``.divineos-<seat>`` convention; asking it, at call time, is the rule
    (the same fault ``sibling_audit_rounds.this_seat`` names: the identity error under every wrong-subject
    bug). The other paths here are shared on purpose and stay under ``.divineos-shared``."""
    from divineos.core.paths import divineos_home

    return divineos_home() / "love_door_shown.json"


SHOWN_FOR_SECONDS = 24 * 3600


def recently_shown(path: Path, now: float) -> frozenset[str]:
    """Record ids shown in the last day. An unreadable file means nothing is known to have been shown."""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return frozenset(k for k, t in data.items() if now - float(t) < SHOWN_FOR_SECONDS)
    except (OSError, ValueError, AttributeError, TypeError):
        return frozenset()


def remember_shown(path: Path, ids: list[str], now: float) -> None:
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = {k: t for k, t in data.items() if now - float(t) < SHOWN_FOR_SECONDS}
    data.update({i: now for i in ids})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
