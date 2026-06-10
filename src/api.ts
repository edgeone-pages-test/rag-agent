/**
 * Frontend API Client
 *
 * Route mapping:
 *   agents/chat/index.py                 → POST /chat        RAG streaming chat
 *   agents/stop/index.py                 → POST /stop        Abort active run
 *   cloud-functions/history/index.py     → POST /history     Get conversation history
 */

export const API = {
  chat: "/chat",
  stop: "/stop",
  history: "/history",
} as const;

export interface HistoryMessage {
  id: string;
  role: string;
  content: string;
  timestamp: number;
}

export interface StreamCallbacks {
  onTextDelta?: (delta: string) => void;
  onToolInput?: (toolCallId: string, toolName: string, input: string) => void;
  onToolOutput?: (toolCallId: string, output: string) => void;
  onFinish?: (stopped?: boolean) => void;
  onError?: (err: Error) => void;
}

export interface SendMessageOptions {
  endpoint?: string;
}

interface SSEEvent {
  type: string;
  delta?: string;
  toolCallId?: string;
  toolName?: string;
  input?: string;
  output?: string;
  stopped?: boolean;
  errorText?: string;
  messageId?: string;
  id?: string;
}

/**
 * Get conversation history (for restoring chat after page refresh).
 *
 * Note: cloud-functions/history reads `conversation_id` from the request body
 * (BaseHTTPRequestHandler doesn't auto-resolve the makers-conversation-id
 * header into the handler's context like the agents runtime does).
 */
export async function fetchConversationHistory(
  conversationId: string,
): Promise<HistoryMessage[]> {
  if (!conversationId) return [];

  try {
    const res = await fetch(API.history, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId }),
    });

    if (!res.ok) return [];

    const data = await res.json().catch(() => null);
    return Array.isArray(data?.messages) ? data.messages : [];
  } catch {
    return [];
  }
}

/**
 * Send a message and receive streaming response.
 *
 * Backend pushes UIMessageStream format events:
 *   - { type: "start", messageId }
 *   - { type: "text-start", id }
 *   - { type: "text-delta", id, delta }
 *   - { type: "text-end", id }
 *   - { type: "tool-input-available", toolCallId, toolName, input }
 *   - { type: "tool-output-available", toolCallId, output }
 *   - { type: "finish", stopped? }
 *   - { type: "error", errorText }
 *
 * @returns AbortController — can be used to abort from frontend
 */
export function sendMessageStream(
  message: string,
  callbacks: StreamCallbacks,
  conversationId: string,
  options: SendMessageOptions = {},
): AbortController {
  const ctrl = new AbortController();
  const endpoint = options.endpoint || API.chat;

  (async () => {
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (conversationId) {
        headers["makers-conversation-id"] = conversationId;
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({ message }),
        signal: ctrl.signal,
      });

      if (!res.ok) {
        callbacks.onError?.(
          new Error(`HTTP ${res.status}: ${await res.text().catch(() => "")}`)
        );
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.(new Error("ReadableStream not supported"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let finishReceived = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE format: events separated by \n\n
        const parts = buffer.split("\n\n");
        // Last segment may be incomplete — keep in buffer
        buffer = parts.pop() || "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed) continue;

          // Parse "data: {...}" line
          const dataLine = trimmed
            .split("\n")
            .find((line) => line.startsWith("data: "));
          if (!dataLine) continue;

          try {
            const event: SSEEvent = JSON.parse(dataLine.slice(6));
            dispatchEvent(event, callbacks, () => {
              finishReceived = true;
            });
          } catch {
            // Ignore parse errors
          }
        }
      }

      // Fallback: trigger finish if backend didn't send finish event
      if (!finishReceived) {
        callbacks.onFinish?.();
      }
    } catch (err) {
      // AbortError does not trigger error callback
      if (err instanceof DOMException && err.name === "AbortError") return;
      callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return ctrl;
}

/**
 * Parse a single SSE event and dispatch to the corresponding callback.
 */
function dispatchEvent(
  event: SSEEvent,
  callbacks: StreamCallbacks,
  markFinish: () => void,
): void {
  if (!event || !event.type) return;

  switch (event.type) {
    case "text-delta":
      callbacks.onTextDelta?.(event.delta ?? "");
      break;
    case "tool-input-available":
      callbacks.onToolInput?.(
        event.toolCallId ?? "",
        event.toolName ?? "",
        event.input ?? "",
      );
      break;
    case "tool-output-available":
      callbacks.onToolOutput?.(event.toolCallId ?? "", event.output ?? "");
      break;
    case "finish":
      markFinish();
      callbacks.onFinish?.(event.stopped);
      break;
    case "error":
      callbacks.onError?.(new Error(event.errorText || "stream error"));
      break;
    // start, text-start, text-end — no special UI handling needed
    default:
      break;
  }
}

/**
 * Request the backend to abort the currently running Agent.
 *
 * IMPORTANT: The stop request must NOT carry the makers-conversation-id header,
 * otherwise the runtime will overwrite chat's signal with stop's signal,
 * causing abortActiveRun to fail. The target conversationId is passed only via body.
 */
export async function stopAgent(conversationId: string): Promise<boolean> {
  try {
    const res = await fetch(API.stop, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
