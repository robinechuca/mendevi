"""Few tools to help display."""

import functools
import numbers

from mendevi.cst.profiles import PROFILES


@functools.cache
def sorted_profiles() -> dict[str, int]:
    """Sort the profiles."""
    profiles = sorted(
        PROFILES, key=lambda p: PROFILES[p]["resolution"][0]*PROFILES[p]["resolution"][1],
    )
    return dict(zip(profiles, range(len(profiles)), strict=True))


def smartsort(item: object) -> object:
    """Make the order relationship more relevant."""
    if isinstance(item, str):
        profiles = sorted_profiles()
        efforts = {"fast": 0, "medium": 1, "slow": 2}  # optional for now because already ordered
        return {**profiles, **efforts}.get(item, item)
    if isinstance(item, numbers.Real):
        return item
    return str(item)
