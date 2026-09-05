"""Regression tests for contextual action prompts and non-button icons."""
import unittest

import qa_align


class ActionLabelTests(unittest.TestCase):
    def test_reviewed_labels(self):
        self.assertEqual(set(qa_align.EXPECTED_ACTION_LABELS),
                         {f"{number:02d}" for number in range(51)})
        for suffix, (english, chinese) in qa_align.EXPECTED_ACTION_LABELS.items():
            with self.subTest(suffix=suffix):
                key = "CommandGuide_00#T_ACT_Command_" + suffix
                self.assertIsNone(qa_align.action_label_mismatch(key, english, chinese))

    def test_previous_mistranslations(self):
        for suffix, previous in (
            ("17", "\u6293\u4f4f\u908a\u7de3"),
            ("44", "\u56de\u6536"),
            ("48", "\u5378\u4e0b"),
        ):
            with self.subTest(suffix=suffix):
                english, chinese = qa_align.EXPECTED_ACTION_LABELS[suffix]
                key = "CommandGuide_00#T_ACT_Command_" + suffix
                self.assertIsNotNone(qa_align.action_label_mismatch(key, english, previous))

    def test_source_drift_and_unreviewed_keys(self):
        key = "CommandGuide_00#T_ACT_Command_17"
        chinese = qa_align.EXPECTED_ACTION_LABELS["17"][1]
        self.assertIsNotNone(qa_align.action_label_mismatch(key, "Grab a ledge", chinese))
        self.assertIsNotNone(qa_align.action_label_mismatch(
            "CommandGuide_00#T_ACT_Command_51", "New action", ""))

    def test_context_specific_wording(self):
        self.assertIsNone(qa_align.action_label_mismatch(
            "message#00605", "Swing", "\u63ee\u821e"))
        self.assertIsNotNone(qa_align.action_label_mismatch(
            "CommandGuide_00#T_ACT_Command_41", "Swing", "\u64fa\u76ea"))
        self.assertIsNotNone(qa_align.action_label_mismatch(
            "CommandGuide_00#T_ACT_Command_29", "Take", "\u62ff\u53d6"))

    def test_formatting_is_not_a_label_change(self):
        english, chinese = qa_align.EXPECTED_ACTION_LABELS["45"]
        prefix = "{0E:0:2:2:00C8}{0E:3:29:0}{0E:0:2:2:0064}"
        self.assertIsNone(qa_align.action_label_mismatch(
            "CommandGuide_00#T_ACT_Command_45", prefix + english, prefix + chinese))

    def test_blocking_registration(self):
        names = {name for name, reason, detector in qa_align.CHECKS}
        for name in ("action-label-mismatch", "nonbutton-icon"):
            self.assertIn(name, names)
            self.assertIn(name, qa_align.BLOCKING)


class NonbuttonIconTests(unittest.TestCase):
    def test_marker_is_not_a_button(self):
        for text in (
            "\u6309{0E:3:14:0}",
            "\u6309\u4e0b {0E:0:3:2:0004}{0E:3:14:0}",
            "\u6309\u4f4f\\n{0E:0:3:2:0004}{0E:3:14:0}",
            "\u9ede\u64ca{0E:3:14:0}",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(qa_align.nonbutton_icon("message#00627", "", text))

    def test_buttons_and_aiming_are_allowed(self):
        for text in (
            "\u6309{0E:3:0:0}",
            "\u6309{0E:3:6:0}\u4f7f\u7528{0E:3:14:0}",
            "\u7528{0E:0:3:2:0004}{0E:3:14:0}\u6a19\u8a18\u76ee\u6a19",
        ):
            with self.subTest(text=text):
                self.assertIsNone(qa_align.nonbutton_icon("message#00627", "", text))


if __name__ == "__main__":
    unittest.main()