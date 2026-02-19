import re


def extract_tags(text: str) -> list[str]:
    tags = re.findall(r"(?<!\#)\#([a-zA-Zа-яА-Я0-9_]+)", text)
    return list(set(t.lower() for t in tags))


def strip_tags(text: str) -> str:
    return re.sub(r"(?<!\#)\#[a-zA-Zа-яА-Я0-9_]+", "", text).strip()


def format_journal_entry(title: str, content: str, tags: list[str] | None, created_at) -> str:
    tags_line = " ".join(f"#{t}" for t in (tags or []))
    date_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""

    return (
        f"# {title}\n\n"
        f"*{date_str}*\n\n"
        f"{tags_line}\n\n"
        f"---\n\n"
        f"{content}"
    )