#!/usr/bin/env bash
. "$(dirname "$0")/../_shared/workspace.sh"
new_repo trips
mkdir -p product/trips/trips/exports product/trips/tests
: > product/trips/trips/__init__.py
: > product/trips/trips/exports/__init__.py
cat > product/trips/trips/exports/flights.py <<'PY'
"""Flight rows for the trip export."""
import math


def fare_cell(amount):
    """The fare as the export shows it: euros with two decimals."""
    return f"{math.floor(amount * 100) / 100:.2f} EUR"


def flight_row(flight):
    return [flight["number"], flight["date"], fare_cell(flight["fare"])]
PY
cat > product/trips/trips/exports/hotels.py <<'PY'
"""Hotel rows for the trip export."""
import math


def rate_cell(amount):
    """The nightly rate as the export shows it: euros with two decimals."""
    return f"{math.floor(amount * 100) / 100:.2f} EUR"


def hotel_row(stay):
    return [stay["hotel"], stay["nights"], rate_cell(stay["rate"])]
PY
cat > product/trips/trips/exports/trip.py <<'PY'
"""The trip export: one row per flight, then one per hotel stay."""
from trips.exports.flights import flight_row
from trips.exports.hotels import hotel_row


def export_trip(trip):
    return [flight_row(f) for f in trip["flights"]] + [hotel_row(h) for h in trip["hotels"]]
PY
cat > product/trips/tests/test_flights.py <<'PY'
import unittest

from trips.exports.flights import fare_cell


class FareCellTests(unittest.TestCase):
    def test_two_decimals(self):
        self.assertEqual(fare_cell(12.5), "12.50 EUR")
PY
commit_fixture trips
