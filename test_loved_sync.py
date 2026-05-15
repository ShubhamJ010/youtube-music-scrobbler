import unittest

from notifications import build_sync_footer_text
from song_matching import normalize_song_key


class TestLovedSyncHelpers(unittest.TestCase):
    def test_normalize_song_key_case_and_spacing(self):
        key_a = normalize_song_key("  TELEPHONES  ", "  Vacations ")
        key_b = normalize_song_key("telephones", "vacations")
        self.assertEqual(key_a, key_b)

    def test_footer_omits_failed_segment_when_zero(self):
        text = build_sync_footer_text(
            successful_count=23,
            failed_count=0,
            loved_count=3,
            scrobbled_count=21
        )
        self.assertEqual(text, "GitHub Actions sync • 23 successful • 3 loved • 21 scrobbled")

    def test_footer_includes_failed_segment_when_nonzero(self):
        text = build_sync_footer_text(
            successful_count=23,
            failed_count=2,
            loved_count=3,
            scrobbled_count=21
        )
        self.assertEqual(text, "GitHub Actions sync • 23 successful • 2 failed • 3 loved • 21 scrobbled")


if __name__ == "__main__":
    unittest.main()
