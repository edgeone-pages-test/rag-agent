"""POST /stop - Abort active agent run."""

from typing import Any

from .._logger import create_logger
from ..chat._stream import _parse_body

logger = create_logger("stop")


async def handler(context: Any):
    """Abort the active agent run for a conversation."""
    body = _parse_body(context)
    conversation_id = body.get("conversation_id", "")

    logger.log(f"Stop request, conversationId: {conversation_id}")

    if not conversation_id:
        logger.error("Missing conversation_id")
        return {"error": "Missing conversation_id"}

    # Attempt to abort via context.utils
    result = context.utils.abort_active_run(conversation_id)
    aborted = getattr(result, "aborted", False) if result else False
    logger.log(f"abortActiveRun result: aborted={aborted}")
    return {
        "status": "aborting" if aborted else "idle",
        "conversationId": conversation_id,
        "aborted": aborted,
    }
