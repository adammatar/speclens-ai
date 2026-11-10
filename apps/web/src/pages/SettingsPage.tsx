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
          <label htmlFor="settings-lang">{t("settings.language")}</label>
          <select
            id="settings-lang"
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
          <label htmlFor="settings-key">{t("settings.sessionKey")}</label>
          <input id="settings-key" readOnly value={apiKey ? "••••••••••••••••" : ""} />
        </div>
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
          {t("settings.sessionHint")}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.deployment")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          {meta?.deployment_mode ?? "…"} · version {meta?.version ?? "…"}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.authState")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          {meta?.auth_required ? t("settings.authRequired") : t("settings.authOpen")}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.providers")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          Embeddings {meta?.embedding_backend ?? "…"} · Generation{" "}
          {meta?.generation_backend ?? "…"} · Extraction {meta?.extraction_backend ?? "…"}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.retention")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          {meta?.retention_days ?? "—"} days
          <br />
          {t("settings.retentionHint")}
        </p>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("settings.securityLimits")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          {t("settings.securityBody")}
        </p>
      </div>
    </div>
  );
}
