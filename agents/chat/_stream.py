"""Shared streaming logic for chat handlers."""

import json
import traceback
from typing import Any, AsyncGenerator

from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent

from .._logger import create_logger


def _sse(data: dict) -> str:
    """Format a single SSE data event for the frontend."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_body(context: Any) -> dict:
    """Extract request body as dict from context."""
    body = context.request.body if hasattr(context.request, "body") else {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {}
    return body if isinstance(body, dict) else {}


async def stream_chat(
    agent,
    message: str,
    context: Any,
    logger,
    max_turns: int = 6,
) -> AsyncGenerator[str, None]:
    """Run an agent with streaming and yield SSE events.

    Handles text deltas, tool calls, tool outputs, cancellation, and errors.
    """
    cancel_signal = getattr(context.request, "signal", None) if hasattr(context, "request") else None

    # Wire up the OpenAI Agents SDK Session backed by EdgeOne `context.store`,
    # so each run reads previous messages and appends new ones automatically.
    session = None
    conversation_id = getattr(context, "conversation_id", "")
    store = getattr(context, "store", None)
    if store and conversation_id and hasattr(store, "openai_session"):
        try:
            session = store.openai_session(conversation_id)
        except Exception as e:
            logger.error(f"Failed to create openai_session: {e}")

    try:
        result = Runner.run_streamed(agent, input=message, max_turns=max_turns, session=session)

        yield _sse({"type": "start", "messageId": f"msg_{id(result)}"})

        current_text_id = None

        async for event in result.stream_events():
            if cancel_signal and hasattr(cancel_signal, "is_set") and cancel_signal.is_set():
                logger.log("Request cancelled")
                yield _sse({"type": "finish", "stopped": True})
                return

            # Text delta
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta = event.data.delta
                if delta:
                    if not current_text_id:
                        current_text_id = f"txt_{id(event)}"
                        yield _sse({"type": "text-start", "id": current_text_id})
                    yield _sse({"type": "text-delta", "id": current_text_id, "delta": delta})

            # Tool events
            elif event.type == "run_item_stream_event":
                if event.name == "tool_called":
                    if current_text_id:
                        yield _sse({"type": "text-end", "id": current_text_id})
                        current_text_id = None

                    item = event.item
                    if hasattr(item, "raw_item") and item.raw_item:
                        raw = item.raw_item
                        call_id = getattr(raw, "call_id", "") or getattr(raw, "id", "") or ""
                        tool_name = getattr(raw, "name", "") or ""
                        arguments = getattr(raw, "arguments", "") or ""

                        parsed_input = {}
                        try:
                            if arguments:
                                parsed_input = json.loads(arguments)
                        except json.JSONDecodeError:
                            parsed_input = {"_raw": arguments}

                        yield _sse({
                            "type": "tool-input-available",
                            "toolCallId": call_id,
                            "toolName": tool_name,
                            "input": parsed_input,
                        })

                elif event.name == "tool_output":
                    item = event.item
                    output = getattr(item, "output", None)
                    raw_item = getattr(item, "raw_item", None)
                    call_id = getattr(raw_item, "call_id", "") if raw_item else ""

                    parsed_output = output
                    if isinstance(output, str):
                        try:
                            parsed_output = json.loads(output)
                        except json.JSONDecodeError:
                            pass

                    yield _sse({
                        "type": "tool-output-available",
                        "toolCallId": call_id,
                        "output": parsed_output,
                    })

        if current_text_id:
            yield _sse({"type": "text-end", "id": current_text_id})

        yield _sse({"type": "finish"})

    except Exception as e:
        logger.error(f"streamChat error: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        yield _sse({"type": "error", "errorText": f"{type(e).__name__}: {e}"})
