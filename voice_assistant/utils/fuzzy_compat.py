"""
Compatibility layer for fuzzy string matching.

Tries fuzzywuzzy first, then rapidfuzz, and finally falls back to
difflib.SequenceMatcher so packaged builds keep working.
"""

from difflib import SequenceMatcher


class _FallbackFuzz:
    @staticmethod
    def ratio(a: str, b: str) -> int:
        return int(round(SequenceMatcher(None, str(a), str(b)).ratio() * 100))

    @staticmethod
    def partial_ratio(a: str, b: str) -> int:
        a = str(a)
        b = str(b)
        if not a or not b:
            return 0
        if len(a) > len(b):
            a, b = b, a
        best = 0
        alen = len(a)
        for i in range(0, len(b) - alen + 1):
            score = SequenceMatcher(None, a, b[i : i + alen]).ratio()
            if score > best:
                best = score
        return int(round(best * 100))


try:
    # Preferred in existing codebase.
    from fuzzywuzzy import fuzz as fuzz  # type: ignore
except Exception:
    try:
        # Fast optional fallback if available.
        from rapidfuzz import fuzz as fuzz  # type: ignore
    except Exception:
        fuzz = _FallbackFuzz()

