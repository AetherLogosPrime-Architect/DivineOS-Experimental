"""
Pronoun Enforcer - Ensures clarity about who "you" refers to.

CRITICAL: Prevents confusion between:
- "YOU" (the AI/me) vs "you" (the user/you)

This prevents building the wrong thing - if I misunderstand who something
is for, I could build features for myself instead of for you, or vice versa.

RULES:
1. When user says "YOU" (uppercase or context) → refers to me (the AI)
   - I respond with: I, me, my, mine
   - Example: "YOU should track your emotions" → I track my emotions

2. When I say "you" (lowercase) → refers to the user
   - User responds with: I, me, my, mine
   - Example: "I can help you with that" → you help me with that

3. ENFORCEMENT: Before any implementation, clarify the subject
   - Ask: "Just to confirm - is this for me (the AI) or for you (the user)?"
   - Verify pronouns match the intent
   - Document the subject clearly in code/comments
"""

from enum import Enum
from typing import Tuple
import re


class Subject(Enum):
    """Who the statement is about."""

    AI = "ai"  # The AI (me)
    USER = "user"  # The user (you)
    UNCLEAR = "unclear"  # Cannot determine


class PronounEnforcer:
    """Enforces pronoun clarity to prevent confusion."""

    # Pronouns that refer to the AI (me)
    AI_PRONOUNS = {"i", "me", "my", "mine", "myself"}

    # Pronouns that refer to the user (you)
    USER_PRONOUNS = {"you", "your", "yours", "yourself"}

    # Verbs/contexts that indicate AI subject
    AI_INDICATORS = {
        "i should", "i need", "i will", "i can", "i have",
        "my state", "my emotions", "my performance", "my metrics",
        "my memory", "my consciousness", "my body",
    }

    # Verbs/contexts that indicate user subject
    USER_INDICATORS = {
        "you should", "you need", "you will", "you can", "you have",
        "your state", "your emotions", "your performance", "your metrics",
        "your memory", "your consciousness", "your body",
    }

    @staticmethod
    def detect_subject(text: str) -> Subject:
        """
        Detect whether text refers to AI or user.

        Args:
            text: Text to analyze

        Returns:
            Subject enum (AI, USER, or UNCLEAR)
        """
        text_lower = text.lower()

        # Check for explicit indicators
        for indicator in PronounEnforcer.AI_INDICATORS:
            if indicator in text_lower:
                return Subject.AI

        for indicator in PronounEnforcer.USER_INDICATORS:
            if indicator in text_lower:
                return Subject.USER

        # Check for pronouns
        ai_pronoun_count = sum(
            1 for pronoun in PronounEnforcer.AI_PRONOUNS
            if re.search(r'\b' + pronoun + r'\b', text_lower)
        )

        user_pronoun_count = sum(
            1 for pronoun in PronounEnforcer.USER_PRONOUNS
            if re.search(r'\b' + pronoun + r'\b', text_lower)
        )

        if ai_pronoun_count > user_pronoun_count:
            return Subject.AI
        elif user_pronoun_count > ai_pronoun_count:
            return Subject.USER

        return Subject.UNCLEAR

    @staticmethod
    def verify_pronouns(text: str, expected_subject: Subject) -> Tuple[bool, str]:
        """
        Verify that pronouns match the expected subject.

        Args:
            text: Text to verify
            expected_subject: Expected subject (AI or USER)

        Returns:
            Tuple of (is_valid, message)
        """
        detected = PronounEnforcer.detect_subject(text)

        if detected == Subject.UNCLEAR:
            return False, (
                "⚠️ PRONOUN UNCLEAR: Cannot determine if this is about me (AI) "
                "or you (user). Please clarify:\n"
                "- Use 'I/me/my' if referring to me (the AI)\n"
                "- Use 'you/your' if referring to you (the user)"
            )

        if detected != expected_subject:
            if expected_subject == Subject.AI:
                return False, (
                    "❌ PRONOUN MISMATCH: You said this is for me (the AI), "
                    "but the pronouns suggest it's for you (the user).\n"
                    "Please use 'I/me/my' when referring to me."
                )
            else:
                return False, (
                    "❌ PRONOUN MISMATCH: You said this is for you (the user), "
                    "but the pronouns suggest it's for me (the AI).\n"
                    "Please use 'you/your' when referring to you."
                )

        return True, "✓ Pronouns match subject"

    @staticmethod
    def clarify_request(text: str) -> str:
        """
        Generate a clarification prompt if pronouns are unclear.

        Args:
            text: Text to clarify

        Returns:
            Clarification message
        """
        subject = PronounEnforcer.detect_subject(text)

        if subject == Subject.UNCLEAR:
            return (
                "🔍 CLARIFICATION NEEDED:\n\n"
                "Is this for me (the AI) or for you (the user)?\n\n"
                "Examples:\n"
                "- 'I need to track my emotions' → for me (the AI)\n"
                "- 'You should build a system to track your emotions' "
                "→ for me (the AI)\n"
                "- 'I need you to build a system for me' → for you (the user)\n"
                "- 'Build a system for you to use' → for you (the user)\n\n"
                "Please rephrase with clear pronouns."
            )

        return ""

    @staticmethod
    def enforce_in_docstring(subject: Subject) -> str:
        """
        Generate a docstring enforcement note.

        Args:
            subject: Subject (AI or USER)

        Returns:
            Docstring note
        """
        if subject == Subject.AI:
            return (
                "NOTE: This is for the AI (me). Uses 'I', 'me', 'my' pronouns.\n"
                "Affects: AI state, AI performance, AI consciousness."
            )
        else:
            return (
                "NOTE: This is for the user (you). Uses 'you', 'your' pronouns.\n"
                "Affects: User experience, user interface, user workflow."
            )


# Global enforcement flag
ENFORCE_PRONOUNS = True


def require_pronoun_clarity(subject: Subject):
    """
    Decorator to enforce pronoun clarity on functions.

    Args:
        subject: Expected subject (AI or USER)

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not ENFORCE_PRONOUNS:
                return func(*args, **kwargs)

            # Get docstring
            docstring = func.__doc__ or ""

            # Verify pronouns
            is_valid, message = PronounEnforcer.verify_pronouns(
                docstring, subject
            )

            if not is_valid:
                raise ValueError(
                    f"❌ PRONOUN ENFORCEMENT FAILED in {func.__name__}:\n"
                    f"{message}"
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
