"""POST /chat - RAG streaming chat with tool use."""

from typing import Any, AsyncGenerator

from .._agent import rag_agent
from .._logger import create_logger
from ._stream import _parse_body, _sse, stream_chat

logger = create_logger("chat")


async def handler(context: Any) -> AsyncGenerator[str, None]:
    body = _parse_body(context)
    message = body.get("message", "")

    if not message or not message.strip():
        logger.error("Missing message field")
        yield _sse({"type": "error", "errorText": "'message' is required"})
        return

    logger.log(f"Starting RAG chat, message: \"{message[:50]}\"")

    async for chunk in stream_chat(rag_agent, message, context, logger, max_turns=6):
        yield chunk

    logger.log("RAG chat completed")
