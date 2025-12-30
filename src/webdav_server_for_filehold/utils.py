import re


def sanitize_name(name: str | None) -> str:
    """
    Sanitizes a filename by replacing invalid characters with underscores.

    Keeps alphanumeric characters, spaces, hyphens, underscores, dots, and parentheses.
    Strips leading and trailing whitespace. Returns "Unknown" if the input name is None or empty.

    Args:
        name (str | None): The filename to sanitize.

    Returns:
        str: The sanitized filename.
    """
    if not name:
        return "Unknown"

    s = re.sub(r'[^\w\s\.\-\(\)]', '_', name)
    return s.strip()


