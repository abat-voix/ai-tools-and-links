import unittest

from search import dot, normalize, rank


class SearchTests(unittest.TestCase):
    def test_normalization_preserves_direction(self) -> None:
        self.assertEqual(normalize([3.0, 4.0]), [0.6, 0.8])
        self.assertAlmostEqual(dot(normalize([3.0, 4.0]), normalize([3.0, 4.0])), 1)

    def test_norm_can_change_raw_dot_ranking(self) -> None:
        query = [1.0, 0.0]
        focused, long = [1.0, 0.1], [10.0, 10.0]
        self.assertGreater(dot(query, long), dot(query, focused))
        result = rank(query, [
            {"id": "focused", "vector": focused},
            {"id": "long", "vector": long},
        ], threshold=-1)
        self.assertEqual([item["id"] for item in result], ["focused", "long"])

    def test_threshold_and_empty_result(self) -> None:
        docs = [{"id": "a", "vector": [0.8, 0.6]}]
        self.assertEqual(rank([1.0, 0.0], docs, 0.8)[0]["id"], "a")
        self.assertEqual(rank([1.0, 0.0], docs, 0.81), [])

    def test_tie_is_stable_by_id(self) -> None:
        docs = [
            {"id": "b", "vector": [1.0, 0.0]},
            {"id": "a", "vector": [1.0, 0.0]},
        ]
        self.assertEqual([item["id"] for item in rank([1.0, 0.0], docs)], ["a", "b"])

    def test_invalid_vectors(self) -> None:
        for vector in [[], [0.0, 0.0], [float("nan")], [float("inf")]]:
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                normalize(vector)
        with self.assertRaises(ValueError):
            dot([1.0], [1.0, 2.0])
        with self.assertRaises(ValueError):
            rank([1.0], [], threshold=1.1)


if __name__ == "__main__":
    unittest.main()
