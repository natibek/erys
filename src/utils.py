import random

DOUBLE_CLICK_INTERVAL = 0.4  # seconds


def generate_id() -> str:
    return "who" + str(random.randint(20, 200))
