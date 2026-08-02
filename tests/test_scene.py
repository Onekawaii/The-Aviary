from __future__ import annotations

import unittest

from aviary.scene import BIRD_ARCHETYPES, Scene, SceneNode, SceneValidationError, Transform


class SceneTests(unittest.TestCase):
    def test_scene_receipt_is_deterministic_across_node_order(self):
        raven = SceneNode("raven-1", "bird", Transform(x=40, y=20), layer=2, props={"archetype": "raven"})
        owl = SceneNode("owl-1", "bird", Transform(x=10, y=15), layer=1, props={"archetype": "owl"})
        first = Scene("archive", "Archive", nodes=(raven, owl))
        second = Scene("archive", "Archive", nodes=(owl, raven))
        self.assertEqual(first.canonical_json(), second.canonical_json())
        self.assertEqual(first.receipt_hash(), second.receipt_hash())

    def test_duplicate_node_ids_fail(self):
        node = SceneNode("same", "bird")
        with self.assertRaisesRegex(SceneValidationError, "duplicate"):
            Scene("bad", "Bad", nodes=(node, node)).validate()

    def test_zero_scale_fails(self):
        with self.assertRaisesRegex(SceneValidationError, "scale"):
            SceneNode("bad", "bird", Transform(scale_x=0)).validate()

    def test_props_must_be_json_serializable(self):
        with self.assertRaisesRegex(SceneValidationError, "JSON"):
            SceneNode("bad", "bird", props={"broken": object()}).validate()

    def test_full_aviary_catalog_is_available(self):
        expected = {"duck", "goose", "raven", "gobble", "owl", "penguin", "eagle", "parrot", "swan", "rooster", "bat", "hummingbird", "dodo", "paracletheon", "brother_ape"}
        self.assertTrue(expected.issubset(set(BIRD_ARCHETYPES)))


if __name__ == "__main__":
    unittest.main()
