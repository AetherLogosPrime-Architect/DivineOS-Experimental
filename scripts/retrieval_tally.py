"""Retrieval-tally command line. The logic moved into the package 2026-10-08.

    python scripts/retrieval_tally.py summary [--days N]
    python scripts/retrieval_tally.py check <reply-file>

This file only forwards to ``divineos.core.retrieval_tally``, where the tally lives and
where the end-of-reply door calls it. It keeps no logic of its own.
"""

import sys

from divineos.core.retrieval_tally import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
