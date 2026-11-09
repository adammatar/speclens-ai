import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createConversation, listConversations, postMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { AnswerTurn, ConversationSummary } from "../lib/types";

export function ChatPage() {
  const { id } = useParams();
  const { apiKey } = useAuth();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerTurn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!apiKey) return;
    listConversations(apiKey)
      .then(setConversations)
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [apiKey]);

  async function onCreate() {
    if (!apiKey) return;
    const conv = await createConversation(apiKey, "Workspace chat");
    setConversations((prev) => [conv, ...prev]);
    navigate(`/chat/${conv.id}`);
  }

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    if (!apiKey || !id || !question.trim()) return;
    setBusy(true);
    setError(null);
    setAnswer(null); // clear previous turn so stub answers cannot linger after Gemini errors
    try {
      const turn = await postMessage(apiKey, id, question.trim());
      setAnswer(turn);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Cited chat</h1>
          <p>Answers are grounded in retrieved chunks; citations are allow-listed.</p>
        </div>
        <button className="btn amber" type="button" onClick={onCreate}>
          New conversation
        </button>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="list">
        {conversations.map((conv) => (
          <Link
            key={conv.id}
            className="list-item"
            to={`/chat/${conv.id}`}
            style={{ fontWeight: conv.id === id ? 600 : 400 }}
          >
            <span>{conv.title}</span>
            <span className="muted">{new Date(conv.updated_at).toLocaleString()}</span>
          </Link>
        ))}
      </div>
      {id ? (
        <form className="stack" onSubmit={onAsk} style={{ maxWidth: 720 }}>
          <div className="field">
            <label htmlFor="q">Question</label>
            <textarea
              id="q"
              rows={4}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What does the spec say about retention?"
            />
          </div>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Retrieving…" : "Ask"}
          </button>
        </form>
      ) : (
        <p className="muted">Select or create a conversation to ask a question.</p>
      )}
      {answer ? (
        <section className="stack">
          <h2>Answer</h2>
          <p className="muted">
            {answer.status} · retrieval {answer.retrieval_status} · generation{" "}
            {answer.generation_status}
            {answer.generation_backend ? ` · backend ${answer.generation_backend}` : ""}
            {answer.model ? ` · model ${answer.model}` : ""}
          </p>
          <p className="prose">{answer.content}</p>
          <p className="muted">
            Citations: {(answer.citation_chunk_ids || []).join(", ") || "none"}
          </p>
        </section>
      ) : null}
    </div>
  );
}
