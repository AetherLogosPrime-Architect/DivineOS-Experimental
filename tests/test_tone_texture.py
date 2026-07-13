"""Tests for tone texture — richer emotional context preservation."""

from divineos.core.knowledge import init_knowledge_table
from divineos.core.tone_texture import (
    classify_tone_rich,
    compute_emotional_arc,
    format_tone_insight,
    get_tone_history,
    init_tone_texture_table,
    record_session_tone,
)


def _setup():
    init_knowledge_table()
    init_tone_texture_table()


class TestClassifyToneRich:
    def test_positive_encouraging(self):
        result = classify_tone_rich("perfect, that looks great!")
        assert result["tone"] == "positive"
        assert result["sub_tone"] == "encouraging"
        assert result["intensity"] > 0.3

    def test_positive_excited(self):
        result = classify_tone_rich("yes!! lets go!!")
        assert result["tone"] == "positive"
        assert result["sub_tone"] == "excited"
        assert result["intensity"] > 0.5

    def test_positive_grateful(self):
        # "thank you" + "wonderful" triggers both grateful sub-tone and positive base tone
        result = classify_tone_rich("thank you so much, that was wonderful and helpful")
        assert result["tone"] == "positive"
        assert result["sub_tone"] == "grateful"

    def test_negative_frustrated(self):
        result = classify_tone_rich("sigh, i already told you not to do that")
        assert result["tone"] == "negative"
        assert result["sub_tone"] == "frustrated"
        assert result["intensity"] > 0.5

    def test_negative_confused(self):
        # "why did you" triggers correction (negative base) + confusion sub-tone
        result = classify_tone_rich("why did you do that? i don't understand")
        assert result["tone"] == "negative"
        assert result["sub_tone"] == "confused"

    def test_negative_disappointed(self):
        result = classify_tone_rich("i expected something different, that's not quite right")
        assert result["tone"] == "negative"
        assert result["sub_tone"] == "disappointed"

    def test_negative_corrective(self):
        result = classify_tone_rich("no, don't use that approach")
        assert result["tone"] == "negative"
        assert result["sub_tone"] == "corrective"

    def test_neutral_questioning(self):
        result = classify_tone_rich("how does the auth module work?")
        assert result["tone"] == "neutral"
        assert result["sub_tone"] == "questioning"

    def test_neutral_informational(self):
        result = classify_tone_rich("the database is in postgres")
        assert result["tone"] == "neutral"
        assert result["sub_tone"] == "informational"

    def test_intensity_increases_with_signals(self):
        low = classify_tone_rich("wrong")
        high = classify_tone_rich("that's wrong, stop doing that, don't use this approach")
        assert high["intensity"] > low["intensity"]

    def test_exclamation_boosts_intensity(self):
        calm = classify_tone_rich("perfect")
        excited = classify_tone_rich("perfect!!!")
        assert excited["intensity"] >= calm["intensity"]


class TestComputeEmotionalArc:
    def test_empty_sequence(self):
        arc = compute_emotional_arc([])
        assert arc["arc_type"] == "silent"
        assert arc["narrative"] == ""

    def test_steady_positive(self):
        seq = [
            {
                "tone": "positive",
                "sub_tone": "encouraging",
                "intensity": 0.5,
                "text": "great",
                "sequence": i,
            }
            for i in range(5)
        ]
        arc = compute_emotional_arc(seq)
        assert arc["arc_type"] == "steady_positive"
        assert arc["overall_tone"] == "positive"
        assert arc["peak_intensity"] == 0.5

    def test_recovery_arc(self):
        seq = [
            {
                "tone": "positive",
                "sub_tone": "encouraging",
                "intensity": 0.4,
                "text": "good start",
                "sequence": 1,
            },
            {
                "tone": "positive",
                "sub_tone": "encouraging",
                "intensity": 0.4,
                "text": "nice",
                "sequence": 2,
            },
            {
                "tone": "negative",
                "sub_tone": "frustrated",
                "intensity": 0.8,
                "text": "why did you do that",
                "sequence": 3,
            },
            {
                "tone": "negative",
                "sub_tone": "corrective",
                "intensity": 0.6,
                "text": "no not like that",
                "sequence": 4,
            },
            {
                "tone": "positive",
                "sub_tone": "satisfied",
                "intensity": 0.5,
                "text": "ok thats better",
                "sequence": 5,
            },
        ]
        arc = compute_emotional_arc(seq)
        assert arc["arc_type"] == "recovery"
        assert len(arc["upset_triggers"]) > 0
        assert len(arc["recovery_actions"]) > 0
        assert arc["recovery_velocity"] > 0
        assert "recover" in arc["narrative"].lower()

    def test_declining_arc(self):
        seq = [
            {
                "tone": "neutral",
                "sub_tone": "informational",
                "intensity": 0.3,
                "text": "start",
                "sequence": 1,
            },
            {
                "tone": "neutral",
                "sub_tone": "informational",
                "intensity": 0.3,
                "text": "ok",
                "sequence": 2,
            },
            {
                "tone": "negative",
                "sub_tone": "frustrated",
                "intensity": 0.7,
                "text": "this is wrong",
                "sequence": 3,
            },
        ]
        arc = compute_emotional_arc(seq)
        assert arc["arc_type"] == "declining"

    def test_brief_session(self):
        seq = [
            {
                "tone": "positive",
                "sub_tone": "encouraging",
                "intensity": 0.5,
                "text": "thanks",
                "sequence": 1,
            },
        ]
        arc = compute_emotional_arc(seq)
        assert arc["arc_type"] == "brief"

    def test_recovery_velocity(self):
        seq = [
            {
                "tone": "negative",
                "sub_tone": "frustrated",
                "intensity": 0.8,
                "text": "no",
                "sequence": 1,
            },
            {
                "tone": "neutral",
                "sub_tone": "informational",
                "intensity": 0.3,
                "text": "hmm",
                "sequence": 2,
            },
            {
                "tone": "neutral",
                "sub_tone": "informational",
                "intensity": 0.3,
                "text": "ok",
                "sequence": 3,
            },
            {
                "tone": "positive",
                "sub_tone": "encouraging",
                "intensity": 0.5,
                "text": "yes!",
                "sequence": 4,
            },
        ]
        arc = compute_emotional_arc(seq)
        # Recovery velocity: 3 messages from negative (index 0) to positive (index 3)
        assert arc["recovery_velocity"] == 3.0


class TestPersistence:
    def test_record_and_retrieve(self):
        _setup()
        arc = {
            "arc_type": "recovery",
            "overall_tone": "positive",
            "peak_intensity": 0.8,
            "recovery_velocity": 2.5,
            "upset_triggers": ["over-engineering"],
            "recovery_actions": ["simplified"],
            "narrative": "Hit frustration, quickly recovered.",
        }
        record_session_tone("test-session-1", arc)
        history = get_tone_history()
        assert len(history) == 1
        assert history[0]["session_id"] == "test-session-1"
        assert history[0]["arc_type"] == "recovery"
        assert history[0]["peak_intensity"] == 0.8
        assert history[0]["recovery_velocity"] == 2.5
        assert history[0]["upset_count"] == 1
        assert history[0]["recovery_count"] == 1
        assert "recovered" in history[0]["narrative"]

    def test_multiple_sessions(self):
        _setup()
        for i in range(3):
            record_session_tone(
                f"s{i}",
                {
                    "arc_type": "steady",
                    "overall_tone": "positive",
                    "peak_intensity": 0.5,
                    "recovery_velocity": 0.0,
                    "upset_triggers": [],
                    "recovery_actions": [],
                    "narrative": f"Session {i}.",
                },
            )
        history = get_tone_history()
        assert len(history) == 3
        # Newest first
        assert history[0]["session_id"] == "s2"

    def test_upsert(self):
        _setup()
        record_session_tone(
            "s1",
            {
                "arc_type": "declining",
                "overall_tone": "negative",
                "peak_intensity": 0.9,
                "upset_triggers": ["x"],
                "recovery_actions": [],
                "narrative": "bad",
            },
        )
        record_session_tone(
            "s1",
            {
                "arc_type": "recovery",
                "overall_tone": "positive",
                "peak_intensity": 0.5,
                "upset_triggers": [],
                "recovery_actions": [],
                "narrative": "good",
            },
        )
        history = get_tone_history()
        assert len(history) == 1
        assert history[0]["arc_type"] == "recovery"

    def test_empty_history(self):
        _setup()
        assert get_tone_history() == []


class TestFormatToneInsight:
    def test_empty(self):
        assert format_tone_insight([]) == ""

    def test_with_upsets(self):
        history = [
            {
                "arc_type": "recovery",
                "overall_tone": "positive",
                "peak_intensity": 0.8,
                "recovery_velocity": 2.0,
                "upset_count": 2,
                "recovery_count": 2,
                "narrative": "recovered",
            },
            {
                "arc_type": "steady",
                "overall_tone": "positive",
                "peak_intensity": 0.4,
                "recovery_velocity": 0.0,
                "upset_count": 0,
                "recovery_count": 0,
                "narrative": "steady",
            },
        ]
        result = format_tone_insight(history)
        assert "Tone:" in result
        assert "2 upsets" in result
        assert "recovery rate" in result

    def test_no_upsets(self):
        history = [
            {
                "arc_type": "steady_positive",
                "overall_tone": "positive",
                "peak_intensity": 0.4,
                "recovery_velocity": 0.0,
                "upset_count": 0,
                "recovery_count": 0,
                "narrative": "good",
            },
        ]
        result = format_tone_insight(history)
        assert "Tone:" in result
        # No upset/recovery info when there are none
        assert "upset" not in result
