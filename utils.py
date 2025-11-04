import html
import re
import uuid

from schemas import Message, MessagePart


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


async def build_conversation_history(
    original_body: dict, current_response: Message
) -> list[Message]:
    """Build conversation history from original request."""
    history = []
    try:
        params = original_body.get("params", {})
        original_message = params.get("message", {})
        original_parts = original_message.get("parts", [])
        # Extract previous messages from data parts
        for part in original_parts:
            if part.get("kind") == "data" and part.get("data"):
                data_items = part["data"]
                if isinstance(data_items, list):
                    for item in data_items:
                        if (
                            isinstance(item, dict)
                            and item.get("kind") == "text"
                            and item.get("text")
                        ):
                            text = item["text"]
                            # Determine role based on content
                            if text.startswith("<p>") and text.endswith("</p>"):
                                # User message
                                clean_text = re.sub("<[^<]+?>", "", text).strip()
                                history.append(
                                    Message(
                                        role="user",
                                        parts=[
                                            MessagePart(kind="text", text=clean_text)
                                        ],
                                        messageId=str(uuid.uuid4()),
                                        taskId=None,
                                        metadata=None,
                                    )
                                )
                            else:
                                # Assume agent message for non-HTML text
                                history.append(
                                    Message(
                                        role="agent",
                                        parts=[MessagePart(kind="text", text=text)],
                                        messageId=str(uuid.uuid4()),
                                        taskId=None,
                                        metadata=None,
                                    )
                                )
        # Add current response to history
        history.append(current_response)
    except Exception as e:  # noqa: BLE001
        print(f"Error building history: {e}")
        # Fallback: just add current response
        history = [current_response]
    return history
