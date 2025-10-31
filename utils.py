import html
import re


def sanitize_text(raw: str) -> str:
    """
    Basic sanitization:
      - Unescape HTML entities
      - Remove HTML tags
      - Remove non-ascii emojis/symbols (keeps basic punctuation)
      - Collapse whitespace.
    """  # noqa: D205
    if raw is None:
        return ""
    text = html.unescape(raw)
    # strip html tags
    text = re.sub(r"<[^>]+>", "", text)
    # remove URLs
    text = re.sub(r"http\S+", "", text)
    # remove non-ASCII characters (e.g. emojis). Adjust if you want unicode support.
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text
