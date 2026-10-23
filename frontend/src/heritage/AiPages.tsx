import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { Sparkles, Send } from "lucide-react";
import AppShell from "./AppShell";
import { sports } from "./data";
import {
  array,
  record,
  text,
  number,
  request,
  formatDate,
  type RecordData,
} from "./services";
import { DataState } from "./ui";
import useAuthStore from "../stores/authStore";
import { SportIntelSummary } from './BettingIntel';

function numeric(value: unknown, suffix = "") {
  const n = number(value);
  return n === null ? "Unavailable" : `${n.toFixed(2)}${suffix}`;
}
function probability(value: unknown) {
  const n = number(value);
  return n !== null && n >= 0 && n <= 1
    ? `${(n * 100).toFixed(1)}%`
    : "Unavailable";
}
function PickCard({ pick }: { pick: RecordData }) {
  return (
    <article className="fh-pick">
      <span className="fh-eyebrow">
        {text(pick.competition) || "Competition unavailable"}
      </span>
      <h3>
        {text(pick.home_team)} v {text(pick.away_team)}
      </h3>
      <strong>{text(pick.selection) || "Selection unavailable"}</strong>
      <p className="fh-data-note">
        {pick.pick_type === "value" ? "Value comparison" : "Model prediction"}
      </p>
      <div className="fh-pick-metrics">
        <div>
          <small>Model probability</small>
          <b>{probability(pick.model_prob)}</b>
        </div>
        <div>
          <small>Odds-implied probability (with vig)</small>
          <b>{probability(pick.implied_prob)}</b>
        </div>
        <div>
          <small>Decimal odds</small>
          <b>{numeric(pick.decimal_odds)}</b>
        </div>
        <div>
          <small>Edge (percentage points)</small>
          <b>{numeric(pick.edge_pct, " pp")}</b>
        </div>
        <div>
          <small>Expected profit at the API reference stake</small>
          <b>{numeric(pick.expected_value)}</b>
        </div>
        <div>
          <small>API reference stake (units; not advice)</small>
          <b>{numeric(pick.recommended_stake)}</b>
        </div>
        <div>
          <small>Model version</small>
          <b>{text(pick.model_version) || "Unavailable"}</b>
        </div>
        <div>
          <small>Bookmaker</small>
          <b>{text(pick.bookmaker) || "Unavailable"}</b>
        </div>
      </div>
      <p>
        {text(pick.explanation) ||
          "The API does not provide an evidence-grounded explanation for this selection."}
      </p>
      <p className="fh-muted">
        Fixture {String(pick.match_id ?? "unavailable")} ·{" "}
        {formatDate(text(pick.match_date))}
      </p>
      <p className="fh-data-note">
        Prediction: {formatDate(text(pick.prediction_created_at))}. Odds updated:{" "}
        {text(pick.odds_updated_at) ? formatDate(text(pick.odds_updated_at)) : "Unavailable"}.
        Model probabilities are estimates, not guarantees.
      </p>
    </article>
  );
}
function SignInNotice() {
  return (
    <div className="fh-state">
      <h3>Log in to use AI Picks.</h3>
      <p>Your picks and conversations use the existing backend account.</p>
      <Link className="fh-button" to="/login">
        Log in
      </Link>
    </div>
  );
}
export function BestPicksPage() {
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  const [params, setParams] = useSearchParams();
  const sport = params.get("sport") || "Football";
  const competition = params.get("competition") || "";
  const date = params.get("date") || "";
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const controller = useRef<AbortController | null>(null);
  const history = useQuery({
    queryKey: ["heritage-picks", useAuthStore((s) => s.user?.id)],
    queryFn: () => request("/ai-picks"),
    enabled: authenticated,
    retry: false,
  });
  useEffect(() => () => controller.current?.abort(), []);
  const update = (key: string, value: string) => {
    controller.current?.abort();
    setResult(null);
    setError(null);
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  async function generate() {
    setLoading(true);
    setError(null);
    setResult(null);
    const active = new AbortController();
    controller.current = active;
    try {
      setResult(
        await request("/ai-picks/generate", {
          method: "POST",
          signal: AbortSignal.any([active.signal, AbortSignal.timeout(35000)]),
          body: JSON.stringify({
            sport,
            competition: competition || undefined,
            date: date || undefined,
            limit: 10,
          }),
        }),
      );
      void history.refetch();
    } catch (err) {
      if (!active.signal.aborted)
        setError(
          err instanceof Error ? err : new Error("AI Picks is unavailable."),
        );
    } finally {
      if (controller.current === active) setLoading(false);
    }
  }
  const response = record(result);
  const picks = array(response.picks).map(record);
  return (
    <AppShell title="A smarter look at matchday." eyebrow="FOOTBALLHERITAGE AI">
      <SportIntelSummary sport={sport} />
      <section className="fh-card fh-section">
        <span className="fh-eyebrow">
          <Sparkles size={14} /> AI PICKS
        </span>
        <h2>Best picks</h2>
        <p className="fh-muted">
          Inspect the selections returned by the existing statistical service.
          AI Picks never places bets or moves money.
        </p>
        {!authenticated ? (
          <SignInNotice />
        ) : (
          <>
            <div className="fh-filters">
              <label>
                Sport
                <select
                  aria-label="Sport"
                  value={sport}
                  onChange={(event) => update("sport", event.target.value)}
                >
                  {sports.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                Competition
                <select
                  aria-label="Competition"
                  value={competition}
                  onChange={(event) =>
                    update("competition", event.target.value)
                  }
                >
                  <option value="">All competitions</option>
                  {[
                    "Premier League",
                    "La Liga",
                    "Bundesliga",
                    "Champions League",
                    "Europa League",
                  ].map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                Match date
                <input
                  type="date"
                  value={date}
                  onChange={(event) => update("date", event.target.value)}
                />
              </label>
            </div>
            <p className="fh-data-note">
              Football predictions use the active model. Competition and match
              date (UTC) are filtered before ranking. Odds comparisons require
              bookmaker quotes from the last 24 hours; otherwise only the model
              prediction is shown. Reference stakes use one unit.
            </p>
            <button
              className="fh-button"
              disabled={loading || sport !== "Football"}
              onClick={() => void generate()}
            >
              {loading ? "Loading selections…" : "Generate / refresh"}
            </button>
            {loading && (
              <button
                className="fh-button fh-button-secondary"
                onClick={() => controller.current?.abort()}
              >
                Cancel
              </button>
            )}
            {sport !== "Football" && (
              <DataState
                error={
                  new Error(
                    `No ${sport} model is available through this endpoint.`,
                  )
                }
              />
            )}
            {result && text(record(response.summary).message) && (
              <p className="fh-data-note">{text(record(response.summary).message)}</p>
            )}
            {loading || error ? (
              <DataState
                loading={loading}
                error={error}
                retry={() => void generate()}
              />
            ) : picks.length ? (
              <>
                {text(response.generated_at) && (
                  <p className="fh-data-note">
                    Run saved {formatDate(text(response.generated_at))}
                  </p>
                )}
                {picks.map((pick, index) => (
                  <PickCard
                    key={`${String(pick.match_id)}-${index}`}
                    pick={pick}
                  />
                ))}
              </>
            ) : (
              <DataState
                empty={
                  result
                    ? "No returned selections match these filters."
                    : "No picks loaded."
                }
              />
            )}
            <details className="fh-history">
              <summary>Saved analysis runs</summary>
              {history.isPending || history.error ? (
                <DataState
                  loading={history.isPending}
                  error={history.error}
                  retry={() => void history.refetch()}
                />
              ) : array(history.data).length ? (
                array(history.data).map((value) => {
                  const run = record(value);
                  return (
                    <button
                      key={text(run.id)}
                      onClick={() => {
                        setResult(run);
                        setError(null);
                      }}
                    >
                      {text(run.sport)} · {formatDate(text(run.created_at))}
                    </button>
                  );
                })
              ) : (
                <p>No saved runs.</p>
              )}
            </details>
          </>
        )}
        <p className="fh-data-note">
          Probabilities are estimates, not guarantees. Missing fields are
          displayed as unavailable, not invented.
        </p>
      </section>
    </AppShell>
  );
}
interface Message {
  role: "user" | "assistant";
  content: string;
  evidence?: unknown;
  mode?: string;
}
function providerReply(value: unknown): Message {
  if (typeof value === "string") return { role: "assistant", content: value };
  const reply = record(value);
  const content =
    text(reply.reply) ||
    text(reply.message) ||
    text(reply.response) ||
    text(reply.content);
  if (!content)
    throw new Error("The chat provider returned no supported text response.");
  return {
    role: "assistant",
    content,
    evidence: reply.picks ?? reply.evidence ?? reply.predictions,
    mode: text(reply.mode),
  };
}
export function AiChatPage() {
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  const userId = useAuthStore((s) => s.user?.id);
  const [params, setParams] = useSearchParams();
  const conversationId = params.get("conversation") || "";
  const [localMessages, setLocalMessages] = useState<{
    conversation: string;
    messages: Message[];
  }>({ conversation: conversationId, messages: [] });
  const messages =
    localMessages.conversation === conversationId ? localMessages.messages : [];
  const setMessages = (next: Message[], id = conversationId) =>
    setLocalMessages({ conversation: id, messages: next });
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [failed, setFailed] = useState<{ messages: Message[]; requestId: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const history = useQuery({
    queryKey: ["heritage-conversations", userId],
    queryFn: () => request("/ai-picks/conversations"),
    enabled: authenticated,
    retry: false,
  });
  const conversation = useQuery({
    queryKey: ["heritage-conversation", userId, conversationId],
    queryFn: () =>
      request(`/ai-picks/conversations/${encodeURIComponent(conversationId)}`),
    enabled: authenticated && !!conversationId,
    retry: false,
  });
  const loaded = array(conversation.data).flatMap((value) => {
    const row = record(value);
    return (row.role === "user" || row.role === "assistant") &&
      text(row.content)
      ? [{ role: row.role, content: text(row.content), evidence: record(row.metadata).evidence,
          mode: text(record(row.metadata).mode) } as Message]
      : [];
  });
  const displayed = messages.length ? messages : loaded;
  useEffect(() => () => controller.current?.abort(), []);
  async function send(next: Message[], requestId: string = crypto.randomUUID()) {
    setMessages(next);
    setLoading(true);
    setError(null);
    setFailed(null);
    const active = new AbortController();
    controller.current = active;
    try {
      const response = record(
        await request("/ai-picks/chat", {
          method: "POST",
          signal: AbortSignal.any([active.signal, AbortSignal.timeout(35000)]),
          body: JSON.stringify({
            conversation_id: conversationId || undefined,
            request_id: requestId,
            messages: next
              .slice(-30)
              .map(({ role, content }) => ({ role, content })),
          }),
        }),
      );
      setMessages(
        [...next, providerReply(response.reply)],
        text(response.conversation_id) || conversationId,
      );
      if (text(response.conversation_id))
        setParams({ conversation: text(response.conversation_id) });
      void history.refetch();
    } catch (err) {
      setFailed({ messages: next, requestId });
      if (!active.signal.aborted)
        setError(
          err instanceof Error ? err : new Error("Chat is unavailable."),
        );
      else
        setError(
          new Error(
            "Request cancelled. The server may have completed the request.",
          ),
        );
    } finally {
      if (controller.current === active) setLoading(false);
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!prompt.trim() || loading) return;
    const next = [
      ...displayed,
      { role: "user" as const, content: prompt.trim() },
    ];
    setPrompt("");
    void send(next);
  }
  function selectConversation(id: string) {
    controller.current?.abort();
    setMessages([]);
    setPrompt("");
    setError(null);
    setFailed(null);
    setParams(id ? { conversation: id } : {});
  }
  return (
    <AppShell title="Talk through the numbers." eyebrow="FOOTBALLHERITAGE AI">
      <section className="fh-card fh-section">
        <h2>AI Picks Chat</h2>
        <p className="fh-muted">
          Ask about fixtures, predictions or odds. Answers use retrieved model
          evidence and supporting knowledge, with source references you can inspect.
        </p>
        {!authenticated ? (
          <SignInNotice />
        ) : (
          <>
            <div className="fh-conversations">
              <button
                className="fh-button fh-button-secondary"
                disabled={loading}
                onClick={() => selectConversation("")}
              >
                New conversation
              </button>
              <label>
                Conversation
                <select
                  aria-label="Conversation"
                  disabled={loading}
                  value={conversationId}
                  onChange={(event) => selectConversation(event.target.value)}
                >
                  <option value="">New conversation</option>
                  {array(history.data).map((value) => {
                    const item = record(value);
                    return (
                      <option value={text(item.id)} key={text(item.id)}>
                        {text(item.sport) || "Chat"} ·{" "}
                        {formatDate(text(item.updated_at))}
                      </option>
                    );
                  })}
                  {conversationId &&
                    !array(history.data).some(
                      (value) => text(record(value).id) === conversationId,
                    ) && (
                      <option value={conversationId}>
                        Current conversation
                      </option>
                    )}
                </select>
              </label>
            </div>
            {history.error && (
              <DataState
                error={history.error}
                retry={() => void history.refetch()}
              />
            )}
            {conversationId &&
              (conversation.isPending || conversation.error) && (
                <DataState
                  loading={conversation.isPending}
                  error={conversation.error}
                  retry={() => void conversation.refetch()}
                />
              )}
            <div className="fh-chat-messages" aria-live="polite">
              {displayed.length
                ? displayed.map((message, index) => (
                    <article
                      className={`fh-message ${message.role}`}
                      key={index}
                    >
                      <small>
                        {message.role === "user"
                          ? "YOU"
                          : message.mode === "retrieved_evidence" ? "RETRIEVED EVIDENCE" : "RAG EXPLANATION"}
                      </small>
                      <p>{message.content}</p>
                      {message.evidence != null && (
                        <details>
                          <summary>Sources and retrieved evidence</summary>
                          <pre>{JSON.stringify(message.evidence, null, 2)}</pre>
                        </details>
                      )}
                    </article>
                  ))
                : !conversation.isFetching && (
                    <DataState empty="Start with a question." />
                  )}
            </div>
            {error && (
              <DataState
                error={error}
                retry={failed ? () => void send(failed.messages, failed.requestId) : undefined}
              />
            )}
            {loading && <p role="status">Retrieving evidence and preparing a reply…</p>}
            <form className="fh-compose" onSubmit={submit}>
              <label>
                Message
                <textarea
                  aria-label="Message"
                  maxLength={4000}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  disabled={
                    loading || conversation.isFetching || !!conversation.error
                  }
                  placeholder="Ask about a fixture or model result…"
                />
              </label>
              <button
                className="fh-button"
                disabled={
                  loading ||
                  !prompt.trim() ||
                  conversation.isFetching ||
                  !!conversation.error
                }
              >
                <Send size={15} />
                Send
              </button>
              {loading && (
                <button
                  type="button"
                  className="fh-button fh-button-secondary"
                  onClick={() => controller.current?.abort()}
                >
                  Cancel
                </button>
              )}
            </form>
            <p className="fh-data-note">
              The latest 30 messages provide context. Conversations and source
              evidence are saved with your account. If text generation is
              unavailable, the chat shows retrieved evidence directly.
            </p>
          </>
        )}
      </section>
    </AppShell>
  );
}
