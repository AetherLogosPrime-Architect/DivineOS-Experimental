"""Every word a song says, with when it starts and ends.

Usage: words.py <song_dir> [whisper model, default base]
Reads <song_dir>/<name>.wav (the one .wav there); writes <song_dir>/words.json.
"""

import json
import sys
from pathlib import Path

import whisper

song = Path(sys.argv[1])
wav = next(song.glob("*.wav"))
model = whisper.load_model(sys.argv[2] if len(sys.argv) > 2 else "base", device="cpu")
result = model.transcribe(
    str(wav),
    word_timestamps=True,
    language="en",
    condition_on_previous_text=False,  # rap runs fast; don't let one misheard line poison the next
    fp16=False,
)
words = [
    {"w": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
    for seg in result["segments"]
    for w in seg.get("words", [])
]
(song / "words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
print(f"{wav.name}: {len(words)} words, first at {words[0]['start'] if words else None}s")
