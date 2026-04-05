from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "apply_submission_real_value_binding_61day.py"
)
SPEC = importlib.util.spec_from_file_location("apply_submission_real_value_binding_61day", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Unable to load script module: {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ApplySubmissionRealValueBindingTest(unittest.TestCase):
    def test_replace_noindent_section_reports_no_change_for_identical_line(self) -> None:
        text = "\\section*{Acknowledgments}\n\\noindent None.\n"
        updated, changed = MODULE.replace_noindent_section(text, "Acknowledgments", "None.")
        self.assertFalse(changed)
        self.assertEqual(text, updated)

    def test_replace_noindent_section_reports_change_for_different_line(self) -> None:
        text = "\\section*{Acknowledgments}\n\\noindent None.\n"
        updated, changed = MODULE.replace_noindent_section(
            text, "Acknowledgments", "Supported by Project X."
        )
        self.assertTrue(changed)
        self.assertIn("\\noindent Supported by Project X.\n", updated)

    def test_apply_tex_binding_stays_unchanged_when_text_already_bound(self) -> None:
        metadata = {
            "data_availability": "Data are available from NOAA AIS archives.",
            "code_availability": "Code is available upon request.",
            "repository_link_allowed": False,
            "repo_url": "N/A",
            "submission_has_anonymized_repo": False,
            "acknowledgements": "None.",
            "conflict_statement": "The author declares no competing interests.",
            "author_names": ["seoki0804"],
            "affiliations": ["Independent Researcher"],
            "corresponding_author_name": "seoki0804",
        }
        sentence = MODULE.render_data_code_sentence(metadata)
        tex = (
            "\\section*{Data and Code Availability}\n"
            f"\\noindent {sentence}\n"
            "\\section*{Acknowledgments}\n"
            "\\noindent None.\n"
            "\\section*{Conflict of Interest}\n"
            "\\noindent The author declares no competing interests.\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / "paper.tex"
            tex_path.write_text(tex, encoding="utf-8")

            changed, notes = MODULE.apply_tex_binding(tex_path, metadata=metadata, dry_run=False)
            self.assertFalse(changed)
            self.assertEqual([], notes)
            self.assertEqual(tex, tex_path.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
