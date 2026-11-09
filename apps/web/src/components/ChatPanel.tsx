import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";
import {
  createConversation,
  getComparison,
  getConversation,
  getDocument,
  postMessage,
  startComparison,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { humanizeAnswer } from "../lib/format";
import type { ChatDocSelection, ChatMessage } from "../lib/types";

type Props = {
  selectedDocs: ChatDocSelection[];
  onToggleDoc: (doc: ChatDocSelection) => void;
  availableDocs: ChatDocSelection[];
};

const SUGGESTIONS = [
  "When was John born?",
  "Summarize the key points in plain language",
  "What changed in the latest version?",
];

export function ChatPanel({ selectedDocs, onToggleDoc, availableDocs }: Props) {
  const { apiKey } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function ensureConversation(): Promise<string> {
    if (!apiKey) throw new Error("Not signed in");
    if (conversationId) return conversationId;
    const title =
      selectedDocs.length === 1
        ? `Chat · ${selectedDocs[0].title}`
        : selectedDocs.length > 1
          ? `Chat · ${selectedDocs.length} documents`
          : "Workspace chat";
    const conv = await createConversation(apiKey, title);
    setConversationId(conv.id);
    return conv.id;
  }

  async function ask(text: string) {
    if (!apiKey || !text.trim()) return;
    if (!selectedDocs.length) {
      setError("Pick at least one document below the composer before asking.");
      return;
    }
    setError(null);
    setBusy(true);
    const userText = text.trim();
    setQuestion("");
    const optimisticId = `local-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: optimisticId,
        role: "user",
        content: userText,
        status: "completed",
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const cid = await ensureConversation();
      const versionIds = selectedDocs.map((d) => d.versionId);
      const lower = userText.toLowerCase();
      if (lower.includes("changed") || lower.includes("difference") || lower.includes("diff")) {
        await maybeInjectCompareSummary(apiKey, selectedDocs, setMessages);
      }
      const turn = await postMessage(apiKey, cid, userText, versionIds);
      const detail = await getConversation(apiKey, cid);
      setMessages(
        detail.messages.map((m) =>
          m.role === "assistant"
            ? { ...m, content: humanizeAnswer(m.content) }
            : m,
        ),
      );
      if (turn.status === "insufficient_evidence") {
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await ask(question);
  }

  return (
    <section className="panel chat-panel">
      <div className="panel-head">
        <div>
          <h2>Chat</h2>
          <p>Answers stay in plain language, grounded in the documents you pick.</p>
        </div>
        <button
          type="button"
          className="btn secondary sm"
          onClick={() => {
            setConversationId(null);
            setMessages([]);
            setError(null);
          }}
        >
          New chat
        </button>
      </div>

      <div className="chat-thread">
        {!messages.length && !busy ? (
          <div className="empty">
            <p>Ask anything about your selected documents.</p>
            <div className="suggest-row" style={{ justifyContent: "center", marginTop: "0.85rem" }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="suggest" onClick={() => ask(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((m) => (
          <div
            key={m.id}
            className={`bubble ${m.role === "user" ? "user" : "assistant"}`}
          >
            {m.role === "assistant" ? humanizeAnswer(m.content) : m.content}
            {m.role === "assistant" && m.citations?.length ? (
              <div className="cite-note">
                Based on {m.citations.length} source quote
                {m.citations.length === 1 ? "" : "s"} from your documents
              </div>
            ) : null}
          </div>
        ))}

        {busy ? (
          <div className="bubble assistant loading" aria-label="Thinking">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form className="chat-composer" onSubmit={onSubmit}>
        {error ? <div className="error">{error}</div> : null}
        <div className="doc-chips">
          <span className="muted" style={{ fontSize: "0.78rem" }}>
            Searching:
          </span>
          {availableDocs.length === 0 ? (
            <span className="muted" style={{ fontSize: "0.78rem" }}>
              Upload a document to get started
            </span>
          ) : (
            availableDocs.map((doc) => {
              const active = selectedDocs.some((s) => s.documentId === doc.documentId);
              return (
                <button
                  key={doc.documentId}
                  type="button"
                  className={`chip ${active ? "active" : "ghost"}`}
                  onClick={() => onToggleDoc(doc)}
                >
                  {doc.title}
                  {doc.versionNumber > 1 ? ` · v${doc.versionNumber}` : ""}
                </button>
              );
            })
          )}
        </div>
        <div className="composer-row">
          <textarea
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              selectedDocs.length
                ? "Message SpecLens…"
                : "Select at least one document, then ask…"
            }
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask(question);
              }
            }}
          />
          <button className="btn" type="submit" disabled={busy || !question.trim()}>
            Send
          </button>
        </div>
      </form>
    </section>
  );
}

async function maybeInjectCompareSummary(
  apiKey: string,
  selectedDocs: ChatDocSelection[],
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>,
): Promise<void> {
  if (selectedDocs.length !== 1) return;
  const detail = await getDocument(apiKey, selectedDocs[0].documentId);
  const versions = [...detail.versions].sort((a, b) => b.version_number - a.version_number);
  if (versions.length < 2) return;
  const [latest, previous] = versions;
  try {
    const job = await startComparison(apiKey, previous.id, latest.id);
    for (let i = 0; i < 40; i += 1) {
      const cmp = await getComparison(apiKey, job.job_id);
      if (cmp.status === "succeeded") {
        const lines = cmp.changes.slice(0, 5).map((c) => {
          if (c.category === "added") return `• Added: ${c.new_statement || "new requirement"}`;
          if (c.category === "removed") return `• Removed: ${c.old_statement || "prior requirement"}`;
          return `• Changed: ${c.new_statement || c.old_statement || "updated requirement"}`;
        });
        const summary =
          lines.length > 0
            ? `Here’s a plain-language look at what changed between v${previous.version_number} and v${latest.version_number}:\n${lines.join("\n")}`
            : `Versions v${previous.version_number} and v${latest.version_number} were compared; no structured requirement changes were flagged.`;
        setMessages((prev) => [
          ...prev,
          {
            id: `compare-${job.job_id}`,
            role: "assistant",
            content: summary,
            status: "completed",
            created_at: new Date().toISOString(),
          },
        ]);
        return;
      }
      if (cmp.status === "failed") return;
      await new Promise((r) => window.setTimeout(r, 800));
    }
  } catch {
    // optional path
  }
}
