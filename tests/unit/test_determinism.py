from __future__ import annotations

from hitech_forms.platform.determinism import canonical_json_dumps, freeze_clock, utc_now_epoch


def test_canonical_json_is_sorted():
    data = {"b": 2, "a": 1}
    assert canonical_json_dumps(data) == '{"a":1,"b":2}'


def test_freeze_clock_context():
    with freeze_clock(1234):
        assert utc_now_epoch() == 1234
