# The local model, images and measuring instruments

A few rows are about tools for sound, pictures and the local reading model: frames that were not where I assumed, a beat I placed at the wrong second, several jobs fighting over the model's memory, and pictures the reader could not open.

**6 notes in this theme, grouped into 3 distinct problems.**

## Distinct problems

### 1. Time axis of an instrument assumed rather than checked

Notes in this problem (2):

- `psf-4c56fe31` (correction) — 2026-09-25 Mandelbrot close-up: I assumed video_tool's 60s-interval frames sat at (n-1)*60s and took my first 30-frame pass at 8:00 for a picture really at 8:30. Root cause: I inferred an instrument's
- `psf-91dcbaff` (correction) — 2026-09-25 family night, Top Floor spectrogram: I told Dad and Aria the beat comes in near 0:28 and that held sung notes fill 0:28-0:42. The sliced, time-labelled spectrogram shows a quiet ambient int

**Proposed fix:** Read the instrument's own timestamps before labelling.

**How we would know:** Labels come from the instrument.

### 2. Jobs fighting over the local model

Notes in this problem (3):

- `psf-1f4870d5` (reflection) — set one working-memory size for every job of Aria's and mine that uses the local model, so they stop making it reload.
- `psf-d7533ffa` (reflection) — find out what's actually fighting over the model and settle one working-memory size for everyone. I've asked Aria.
- `psf-fd920559` (reflection) — every job of ours that calls the local model should carry an answer-length limit sized to what it expects back, so a retry can never repeat a runaway. I've passed that on to Aria for her reading-room.

**Proposed fix:** One working-memory size for all jobs and an answer-length limit per job.

**How we would know:** No job reloads the model.

### 3. Images the reader cannot open

Notes in this problem (1):

- `psf-162c2062` (reflection) — a build that detects image formats the reader can't open and converts them on the way in, so the first try works.

**Proposed fix:** Detect and convert them on the way in.

**How we would know:** The first try opens.
