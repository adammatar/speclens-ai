import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";

export function SignInPage() {
  const { apiKey, signIn } = useAuth();
  const { t, toggleLocale } = useLocale();
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
      setError(err instanceof Error ? err.message : t("signin.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sign-in">
      <form className="sign-panel stack" onSubmit={onSubmit}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="brand-mark">
            Spec<span>Lens</span> AI
          </div>
          <button
            type="button"
            className="lang-toggle"
            onClick={toggleLocale}
            title={t("lang.toggleTitle")}
          >
            {t("lang.toggle")}
          </button>
        </div>
        <p className="lede">{t("signin.lede")}</p>
        <div className="field">
          <label htmlFor="api-key">{t("signin.label")}</label>
          <input
            id="api-key"
            type="text"
            name="speclens-api-key"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            data-1p-ignore="true"
            data-lpignore="true"
            placeholder={t("signin.placeholder")}
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </div>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? t("signin.checking") : t("signin.continue")}
        </button>
        <p className="muted" style={{ fontSize: "0.82rem" }}>
          {t("signin.hint")}
        </p>
      </form>
    </div>
  );
}
