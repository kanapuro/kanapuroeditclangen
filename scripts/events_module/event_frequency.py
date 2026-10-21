from random import randint


def select_frequency(events):
    if not any(event.frequency is not None for event in events):
        return events

    roll = randint(1, 10)
    frequency = 4 if roll <= 4 else 3 if roll <= 7 else 2 if roll <= 9 else 1
    used = set()
    while frequency not in used:
        pool = [event for event in events if (event.frequency or 4) == frequency]
        if pool:
            return pool
        used.add(frequency)
        if max(used) < 4:
            frequency = max(used) + 1
        elif min(used) > 1:
            frequency = min(used) - 1
    return []
