"""TryFi's GraphQL is exactly what pytryfi sent.

These are the queries that work against TryFi on every install today. A
change to one cannot be checked without an account, and a broken query breaks
every install at once, so each composed query is pinned to the hash of what
pytryfi (disruptivepatternmaterial/pytryfi at cc31b96) composed. If one of
these fails, the change needs testing against a real account first.
"""

from __future__ import annotations

import hashlib

import pytest

from custom_components.tryfi.client import queries

PINNED = {
    "households": "9b6a684555ac69e83e5929ad1137d2eac83d02936d7bd906ae48bc039eebcd7c",
    "location": "7d8e1119993f463a4537dc6df064d122684b6e6490dac45af74609c8e0b6edd2",
    "activity": "b7e5274602635a48ebfd58a9eed131cc08302d1810424230132fe85bfafa03f3",
    "rest": "032b868357ea1ac029f59cee68340a43ba83371ea6298dbec9bd4f6ba5fe4648",
    "set_led_color": "c80cdd45bc37997d46bbf3145af7d756d5dab849e77c17204777e4bf52e1e7b0",
    "device_operation": (
        "efbc04a00f3fc9b99540e3ecfc4909258904112ba3b7b2a23db18cde92441162"
    ),
}

COMPOSED = {
    "households": queries.households(),
    # pytryfi substituted the pet id into the text; "PET" stood in for it
    # when the hashes were taken.
    "location": queries.location("PET"),
    "activity": queries.activity("PET"),
    "rest": queries.rest("PET"),
    "set_led_color": queries.set_led_color(),
    "device_operation": queries.device_operation(),
}


@pytest.mark.parametrize("name", sorted(PINNED))
def test_query_is_unchanged(name: str) -> None:
    digest = hashlib.sha256(COMPOSED[name].encode()).hexdigest()
    assert digest == PINNED[name]
