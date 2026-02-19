def truncate(text: str, max_length: int = 4096) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def escape_markdown(text: str) -> str:
    special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_number(n: int) -> str:
    if n >= 1000000:
        return f"{n / 1000000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)