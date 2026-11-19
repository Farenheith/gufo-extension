"""Catalogue integrity: only metadata from the reviewed source may be published."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import registry


class CatalogueTest(unittest.TestCase):
    def test_snapshot_requires_matching_reviewed_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entries = root / "extensions"
            entries.mkdir()
            revision = "a" * 40
            release = {"version": "1.0.0", "revision": revision,
                       "digest": "sha256:" + "b" * 64, "api_version": ">= 0.3.0",
                       "platforms": ["linux"]}
            entry = {"name": "fixture", "source": "https://example.com/fixture",
                     "releases": [release]}
            (entries / "fixture.json").write_text(json.dumps(entry))

            def fetch(source, rev, destination):
                destination.mkdir()
                manifest = {"name": "fixture", "version": "1.0.0",
                            "api_version": ">= 0.3.0", "platforms": ["linux"],
                            "providers": [{"id": "fixture", "model_ids": ["fixture-small"]}]}
                (destination / "extension.json").write_text(json.dumps(manifest))

            with patch.multiple(registry, ROOT=root, ENTRIES=entries, CATALOG=root / "catalog"), \
                    patch.object(registry, "fetch", fetch), \
                    patch.object(registry, "tree_digest", return_value=release["digest"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(registry.verify("fixture", refresh=True), 0)
                snapshot = root / "catalog" / "fixture" / f"{revision}.json"
                self.assertEqual(registry.verify("fixture"), 0)
                value = json.loads(snapshot.read_text())
                value["providers"][0]["model_ids"] = ["unreviewed"]
                snapshot.write_text(json.dumps(value))
                self.assertEqual(registry.verify("fixture"), 1)
                with patch.object(registry, "tree_digest", return_value="sha256:" + "c" * 64):
                    self.assertEqual(registry.verify("fixture", refresh=True), 1)
                self.assertEqual(json.loads(snapshot.read_text()), value)


if __name__ == "__main__":
    unittest.main()
