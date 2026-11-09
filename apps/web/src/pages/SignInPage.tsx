import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function SignInPage() {
  const { apiKey, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from || "/";

  if (apiKey) {
    return <Navigate to={from} replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(key);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sign-in">
      <form className="sign-panel stack" onSubmit={onSubmit}>
        <div className="brand-mark">
          Spec<span>Lens</span>
        </div>
        <p className="lede">
          Upload specs, chat in plain language, and keep versions side by side —
          built for clear answers with evidence.
        </p>
        <div className="field">
          <label htmlFor="api-key">Workspace API key</label>
          <input
            id="api-key"
            type="text"
            name="speclens-api-key"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            data-1p-ignore="true"
            data-lpignore="true"
            placeholder="Paste your key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </div>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Checking…" : "Continue"}
        </button>
        <p className="muted" style={{ fontSize: "0.82rem" }}>
          The key stays in this browser session only.
        </p>
      </form>
    </div>
  );
}
