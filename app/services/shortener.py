import random

# The 62 characters we use for encoding
# Order matters — this defines what number maps to what character
BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE_LENGTH = 6


def encode_base62(number: int) -> str:
    """Convert a large integer into a Base62 string."""
    if number == 0:
        return BASE62_CHARS[0]

    result = []
    while number > 0:
        remainder = number % 62       # which character does this map to?
        result.append(BASE62_CHARS[remainder])
        number //= 62                 # move to next "digit"

    return "".join(reversed(result))  # reverse because we built it backwards


def generate_short_code() -> str:
    """Generate a random 6-character Base62 short code."""
    # Large random number → encode → take first 6 chars
    random_number = random.randint(100_000_000, 999_999_999)
    code = encode_base62(random_number)
    return code[:CODE_LENGTH]