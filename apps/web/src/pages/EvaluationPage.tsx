import { useEffect, useState } from "react";
import { ApiError, getLatestEvaluation } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";
import type { EvaluationReport } from "../lib/types";

function formatTime(iso: string | undefined, locale: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(locale === "he" ? "he-IL" : "en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Jerusalem",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function EvaluationPage() {
  const { apiKey } = useAuth();
  const { t, locale } = useLocale();
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiKey) return;
    setLoading(true);
    getLatestEvaluation(apiKey)
      .then((data) => {
        setReport(data);
        setMissing(false);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setMissing(true);
          setReport(null);
          setError(null);
        } else {
          setError(err instanceof ApiError ? err.message : t("eval.loadFailed"));
        }
      })
      .finally(() => setLoading(false));
  }, [apiKey, t]);

  if (loading) {
    return (
      <div className="main-pad">
        <p className="muted">{t("eval.loading")}</p>
      </div>
    );
  }

  if (missing) {
    return (
      <div className="main-pad stack" style={{ maxWidth: 640 }}>
        <div className="page-head">
          <div>
            <h1>{t("eval.title")}</h1>
            <p>{t("eval.subtitle")}</p>
          </div>
        </div>
        <p className="empty">{t("eval.none")}</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="main-pad">
        <p className="error-text">{error ?? t("eval.loadFailed")}</p>
      </div>
    );
  }

  const metrics = report.metrics ?? {};
  const gates = report.gates ?? {};
  const baseline = report.baseline_diff ?? {};
  const backends = report.backends ?? {};

  return (
    <div className="main-pad stack">
      <div className="page-head">
        <div>
          <h1>{t("eval.title")}</h1>
          <p>{t("eval.subtitle")}</p>
        </div>
        {report.synthetic_stub_badge || report.mode === "stub" ? (
          <span
            className="badge-stub"
            data-testid="eval-stub-badge"
            title={t("eval.stubCaveat")}
          >
            {t("eval.stubBadge")}
          </span>
        ) : (
          <span className="badge-live">{t("eval.liveBadge")}</span>
        )}
      </div>

      <p className="muted" style={{ fontSize: "0.9rem" }} data-testid="eval-stub-caveat">
        {t("eval.stubCaveat")}
      </p>

      <div className="stats-row">
        <div className="stat">
          <span className="muted">{t("eval.runTime")}</span>
          <strong>{formatTime(report.generated_at, locale)}</strong>
        </div>
        <div className="stat">
          <span className="muted">{t("eval.mode")}</span>
          <strong>{report.mode}</strong>
        </div>
        <div className="stat">
          <span className="muted">{t("eval.dataset")}</span>
          <strong>{report.dataset_version ?? "v1"}</strong>
        </div>
        <div className="stat">
          <span className="muted">{t("eval.samples")}</span>
          <strong>{report.question_like_count ?? "—"}</strong>
        </div>
      </div>

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("eval.backends")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          {Object.entries(backends)
            .map(([k, v]) => `${k}=${v}`)
            .join(" · ") || "—"}
        </p>
      </div>

      <div
        className="table-wrap"
        role="region"
        aria-label={t("eval.metrics")}
        data-testid="eval-metrics-table"
      >
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">{t("eval.metric")}</th>
              <th scope="col">{t("eval.value")}</th>
              <th scope="col">{t("eval.threshold")}</th>
              <th scope="col">{t("eval.gate")}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metrics)
              .filter(([name]) => !name.endsWith("_n") && name !== "n")
              .map(([name, value]) => {
                const gate = gates[name];
                return (
                  <tr key={name} data-testid="eval-metric-row">
                    <td>{name}</td>
                    <td>{typeof value === "number" ? value.toFixed(4) : String(value)}</td>
                    <td>{gate?.threshold ?? "—"}</td>
                    <td
                      className={gate?.status === "fail" ? "fail" : "pass"}
                      data-testid={
                        gate?.status === "pass"
                          ? "eval-gate-pass"
                          : gate?.status === "fail"
                            ? "eval-gate-fail"
                            : "eval-gate-na"
                      }
                    >
                      {gate?.status ?? "n/a"}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {Object.keys(baseline).length > 0 ? (
        <div className="table-wrap" role="region" aria-label={t("eval.baseline")}>
          <h2 style={{ fontSize: "1.05rem" }}>{t("eval.baseline")}</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">{t("eval.metric")}</th>
                <th scope="col">{t("eval.value")}</th>
                <th scope="col">baseline</th>
                <th scope="col">Δ</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(baseline).map(([name, item]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{item.current.toFixed(4)}</td>
                  <td>{item.baseline.toFixed(4)}</td>
                  <td>
                    {item.delta >= 0 ? "+" : ""}
                    {item.delta.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="version-card" style={{ display: "block" }}>
        <strong>{t("eval.latencyCost")}</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          p50 {metrics.latency_p50_ms?.toFixed?.(1) ?? "—"} ms · p95{" "}
          {metrics.latency_p95_ms?.toFixed?.(1) ?? "—"} ms · tokens in{" "}
          {metrics.input_tokens ?? "—"} / out {metrics.output_tokens ?? "—"} · cost{" "}
          {metrics.estimated_cost_usd ?? "—"}
        </p>
      </div>
    </div>
  );
}
