from decimal import Decimal
import pytest
from app.importer import clean


def valid(**changes):
    return dict(reading_id="R-1", vehicle_id="VAN-01", recorded_at="2026-09-23T08:00:00Z", miles="125.25", fuel_gallons="9.1", **{}) | changes


def test_clean_preserves_exact_values_and_time_zone():
    row = clean(valid(miles=" 125.25 "))
    assert row["miles"] == Decimal("125.25")
    assert row["recorded_at"].tzinfo is not None


@pytest.mark.parametrize("changes", [
    {"vehicle_id": ""}, {"reading_id": "bad/id"}, {"miles": "-1"}, {"miles": "NaN"},
    {"miles": "Infinity"}, {"fuel_gallons": "501"}, {"miles": "1.234"},
    {"recorded_at": "yesterday"}, {"recorded_at": "2026-09-23T08:00:00"}, {"miles": None},
])
def test_bad_rows_are_rejected(changes):
    with pytest.raises(ValueError):
        clean(valid(**changes))


def test_zero_is_a_valid_value():
    assert clean(valid(miles="0", fuel_gallons="0"))["miles"] == 0
