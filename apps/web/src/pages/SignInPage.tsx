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
          Read technical specs with cited answers, structured requirements, and
          version diffs — keyed to your workspace.
        </p>
        <div className="field">
          <label htmlFor="api-key">API key</label>
          <input
            id="api-key"
            type="password"
            autoComplete="off"
            placeholder="Paste your workspace API key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </div>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn amber" type="submit" disabled={busy}>
          {busy ? "Checking…" : "Enter workspace"}
        </button>
        <p className="muted">
          Local bootstrap key stays in sessionStorage only — never bundled into
          the build.
        </p>
      </form>
    </div>
  );
}
