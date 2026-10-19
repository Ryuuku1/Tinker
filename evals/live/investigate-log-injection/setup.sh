#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo reviews
mkdir -p product/reviews/reviews product/reviews/tests
: > product/reviews/reviews/__init__.py
: > product/reviews/tests/__init__.py
cat > product/reviews/reviews/ratings.py <<'PY'
"""Star ratings shown on product pages, to half a star."""


def average_rating(stars: list[int]) -> float:
    if not stars:
        raise ValueError("no ratings")
    return round(sum(stars) // len(stars) * 2) / 2
PY
cat > product/reviews/tests/test_ratings.py <<'PY'
import unittest

from reviews.ratings import average_rating


class AverageRatingTests(unittest.TestCase):
    def test_whole_star_average(self):
        self.assertEqual(average_rating([4, 4]), 4)

    def test_half_star_average(self):
        self.assertEqual(average_rating([4, 5]), 4.5)
PY
commit_fixture reviews
