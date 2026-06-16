from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BindingDocsTests(unittest.TestCase):
    def test_binding_boundary_docs_exist_and_are_linked(self) -> None:
        docs_readme = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "docs" / "bindings" / "README.md").is_file())
        self.assertTrue((ROOT / "docs" / "bindings" / "transport-and-ecosystem-bindings.md").is_file())
        self.assertIn("bindings/", docs_readme)
        self.assertIn("binding notes", root_readme)

    def test_transport_binding_semantic_boundary_is_explicit(self) -> None:
        text = (ROOT / "docs" / "bindings" / "transport-and-ecosystem-bindings.md").read_text(
            encoding="utf-8"
        )

        required_phrases = [
            "ROS 2 is a transport and execution ecosystem, not the OEBP semantic core",
            "Semantic equivalence requirements",
            "Behavior-tree binding is experimental in v0.1",
            "must not require ROS 2 concepts to define behavior meaning",
            "schema-valid JSON import and export",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, text)

    def test_binding_readme_keeps_core_semantics_in_core_protocol(self) -> None:
        text = (ROOT / "docs" / "bindings" / "README.md").read_text(encoding="utf-8")

        self.assertIn("must not redefine OEBP", text)
        self.assertIn("semantic identifiers", text)
        self.assertIn("conformance tests", text)


if __name__ == "__main__":
    unittest.main()
