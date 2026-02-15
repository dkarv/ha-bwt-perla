def truncate_value(value: str, max_length: int = 255) -> str:
    """Truncate a string to `max_length` characters, adding ellipsis if needed.

    Returns an empty string for None-like inputs and ensures a string is returned
    even if the input cannot be converted to `str`.
    """
    if value is None:
        return ""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
