# A reply that says a fix waits on Aletheia has sent her the letter (draft, 2026-10-25)

**Author: aether**

## What is wrong

Dad, 2026-10-25: *"you continue to say 'Waits for Aletheia' without sending her a letter lol so that needs fixed."* It is true and it was the same sentence all day. #722 and #723 sat "waiting" for hours with no letter naming them; #701 changed head after the letter that named it, so the letter described a fix that no longer existed. The briefing already counts the fixes she has never been asked about, but it is read once at the start of a session and says nothing at the moment I write the sentence. I told Dad the note would be remembered; a note I must remember is the failure this house keeps meeting.

## What it does

A Stop check, `waiting_claim`, registered beside `landed_claim` (both pair a sentence I wrote with the evidence the sentence needs). It reads my reply, finds a sentence that names one or more pull requests AND Aletheia AND something waiting (wait, waits, waiting, "with Aletheia", "ready for her"), asks GitHub for each pull request's live head, and refuses the reply unless some letter of mine to her names the number and the first seven characters of that head. The refusal names which fixes, at which head, and says to write the letter first (`divineos landing --request` prints the body). A fix that has merged or closed is not asked for. A head that cannot be read is reported as could-not-check, never a pass and never a block.

## What it cannot see

A pronoun in another sentence ("Aletheia has it. #722 is with her now."), a claim made in words that carry neither the number nor her name, and a letter that names the head but never asks her anything. It also fires on a sentence that only DESCRIBES such a claim, which is the mention-and-use problem every keyword layer here has; the cost is one turn spent writing the letter I owed. It is a net for the exact sentence said four times, not proof that she was asked well.

## Falsifier, counted in uses

Of the next 20 times this refuses, if more than 5 were a reply that did not mean "waits on her" (a description, a negation), the net is too wide and is narrowed; if a fix waits on her with no letter after it ships and no refusal fired, it missed and gets a row.
