"""Storyboard rule tests: start from the real storyboard, break one thing,
check the right rule fires. `make test`"""
import copy
import json
import unittest
from pathlib import Path

from pipeline import rules

SB = json.loads((Path(__file__).resolve().parent.parent / "storyboard.json").read_text(encoding="utf-8"))


def findings(mutate):
    sb = copy.deepcopy(SB)
    mutate(sb)
    return rules.check(sb)


def has(fs, level, text):
    return any(f.level == level and text in f.message for f in fs)


class RuleTests(unittest.TestCase):
    def test_real_storyboard_has_no_errors(self):
        self.assertEqual(rules.errors(rules.check(SB)), [])

    def test_too_long_film(self):
        def m(sb):
            for s in sb["shots"]:
                s["duration_s"] = 12
        self.assertTrue(has(findings(m), "ERROR", "exceeds 90s"))

    def test_shot_ids_out_of_order(self):
        def m(sb):
            sb["shots"][0]["id"], sb["shots"][1]["id"] = "s02", "s01"
        self.assertTrue(has(findings(m), "ERROR", "must run s01"))

    def test_missing_reason(self):
        self.assertTrue(has(findings(lambda sb: sb["shots"][2].update(reason="pretty")), "ERROR", "reason is too short"))

    def test_narration_without_subtitle(self):
        self.assertTrue(has(findings(lambda sb: sb["shots"][0].update(subtitle_en="")), "ERROR", "no English subtitle"))

    def test_end_card_must_mention_ai(self):
        self.assertTrue(has(findings(lambda sb: sb["meta"].update(end_card=["Thank you"])), "ERROR", "made with AI"))

    def test_end_card_thank_you_with_ai_label_passes(self):
        card = ["The End", "Thank you for watching", "Made with AI"]
        self.assertFalse(has(findings(lambda sb: sb["meta"].update(end_card=card)), "ERROR", "made with AI"))

    def test_music_cues_gap(self):
        self.assertTrue(has(findings(lambda sb: sb["music"]["cues"].pop(1)), "ERROR", "cover every shot exactly once"))

    def test_music_cues_overlap(self):
        self.assertTrue(has(findings(lambda sb: sb["music"]["cues"][1].update(from_shot="s02")), "ERROR", "overlapping"))

    def test_unknown_reference(self):
        self.assertTrue(has(findings(lambda sb: sb["shots"][0].update(refs=["ref_nope"])), "ERROR", "unknown reference"))

    def test_chosen_music_missing(self):
        self.assertTrue(has(findings(lambda sb: sb["music"].update(chosen="outputs/music/nope.flac")), "ERROR", "file not found"))

    def test_style_instruction_warns(self):
        self.assertTrue(has(findings(lambda sb: sb["meta"]["narration_voice"].update(style="Read calmly:")), "WARNING", "spoken aloud"))

    def test_text_in_image_warns(self):
        self.assertTrue(has(findings(lambda sb: sb["shots"][3].update(image_prompt="a church with a sign over the door")), "WARNING", "garbled"))

    def test_key_in_caption_warns(self):
        self.assertTrue(has(findings(lambda sb: sb["music"].update(caption="instrumental ballad in D minor")), "WARNING", "bpm/key fields"))


if __name__ == "__main__":
    unittest.main()
