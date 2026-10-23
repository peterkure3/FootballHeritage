import { useState } from "react";
import { api } from "../../utils/api";
import AdminPage from "./AdminPage";

const prompts = [
  "Explain today's forecast probabilities",
  "Explain expected value and bookmaker margin",
  "How should I interpret paper trial results?",
];

async function chatRequest(conversation, requestId, messages) {
  const response = await api.aiPicks.chat({
    conversation_id: conversation || undefined,
    request_id: requestId,
    messages: messages.slice(-30),
  });
  if (!response.reply?.reply)
    throw new Error("The assistant returned an empty response.");
  return response;
}

export default function SportsAssistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [failed, setFailed] = useState(null);
  const [conversation, setConversation] = useState(null);
  async function send(text, retryRequest) {
    if (pending || !text.trim()) return;
    const request = retryRequest || {
      requestId: crypto.randomUUID(),
      messages: [...messages, { role: "user", content: text.trim() }],
    };
    const { messages: next, requestId } = request;
    setMessages(next);
    setInput("");
    setError("");
    setPending(true);
    try {
      const response = await chatRequest(conversation, requestId, next);
      setConversation(response.conversation_id);
      setMessages([
        ...next,
        { role: "assistant", content: response.reply.reply },
      ]);
      setFailed(null);
    } catch (failure) {
      setError(failure.message);
      setFailed({ messages: next, requestId });
    } finally {
      setPending(false);
    }
  }
  return (
    <AdminPage
      title="SportsGPT."
      description="Ask the sports assistant about odds, forecasts, and evaluation. Responses depend on the available evidence."
    >
      <article className="admin-panel">
        <h2>Sports analysis assistant</h2>
        {!messages.length && (
          <div className="admin-toolbar">
            {prompts.map((prompt) => (
              <button
                key={prompt}
                className="admin-button"
                onClick={() => send(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
        <div
          className="admin-chat-log"
          role="log"
          aria-label="Assistant conversation"
          aria-live="polite"
        >
          {messages.map((message, index) => (
            <div
              key={index}
              className="admin-chat-message"
              data-role={message.role}
            >
              <strong>{message.role === "user" ? "You" : "SportsGPT"}</strong>
              <p>{message.content}</p>
            </div>
          ))}
          {pending && <p role="status">Reviewing the available evidence…</p>}
        </div>
        {error && (
          <div className="admin-notice admin-error" role="alert">
            {error}
            <button
              className="admin-button"
              disabled={pending}
              onClick={() => send(failed.messages.at(-1).content, failed)}
            >
              Retry response
            </button>
          </div>
        )}
        <form
          className="admin-chat-compose"
          onSubmit={(event) => {
            event.preventDefault();
            send(input);
          }}
        >
          <input
            aria-label="Message SportsGPT"
            maxLength={2000}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about forecasts or paper trials…"
          />
          <button className="admin-button" disabled={pending || !input.trim()}>
            Send
          </button>
        </form>
      </article>
    </AdminPage>
  );
}
