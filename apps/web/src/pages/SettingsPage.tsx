import { useEffect, useState } from "react";
import { getMeta } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLocale, type Locale } from "../lib/i18n";
import type { MetaInfo } from "../lib/types";

export function SettingsPage() {
  const { apiKey } = useAuth();
  const { t, locale, setLocale } = useLocale();
  const [meta, setMeta] = useState<MetaInfo | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <div className="main-pad stack" style={{ maxWidth: 640 }}>
      <div className="page-head">
        <div>
          <h1>{t("settings.title")}</h1>
          <p>{t("settings.subtitle")}</p>
        </div>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <div className="field">
          <label>{t("settings.language")}</label>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
          >
            <option value="en">{t("settings.langEn")}</option>
            <option value="he">{t("settings.langHe")}</option>
          </select>
        </div>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <div className="field">
          <label>{t("settings.sessionKey")}</label>
          <input readOnly value={apiKey ? "••••••••••••••••" : ""} />
        </div>
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
          {t("settings.sessionHint")}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.runtime")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          Version {meta?.version ?? "…"} · mode {meta?.deployment_mode ?? "…"}
          <br />
          Embeddings {meta?.embedding_backend ?? "…"} · Generation{" "}
          {meta?.generation_backend ?? "…"} · Extraction {meta?.extraction_backend ?? "…"}
          <br />
          Retention {meta?.retention_days ?? "—"} days · Auth{" "}
          {meta?.auth_required ? t("settings.authRequired") : t("settings.authOpen")}
        </p>
      </div>
    </div>
  );
}
