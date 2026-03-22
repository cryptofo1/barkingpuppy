"""XP / leveling math and helpers."""


def xp_for_level(level: int) -> int:
    """Total XP needed to reach *level* (quadratic curve).

    Formula: 5 * level^2 + 50 * level + 100
    Level 1 = 155 XP, Level 10 = 1100 XP, Level 50 = 15 600 XP.
    """
    return 5 * level * level + 50 * level + 100


def level_from_xp(xp: int) -> int:
    """Return the highest level achievable with the given XP."""
    level = 0
    while xp >= xp_for_level(level + 1):
        xp -= xp_for_level(level + 1)
        level += 1
    return level


def xp_progress(xp: int, level: int) -> tuple[int, int]:
    """Return (current_xp_in_level, xp_needed_for_next_level)."""
    spent = sum(xp_for_level(lvl) for lvl in range(1, level + 1))
    current = xp - spent
    needed = xp_for_level(level + 1)
    return current, needed
