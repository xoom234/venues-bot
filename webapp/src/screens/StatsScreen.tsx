import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { haptic } from "../tg";
import type { Venue } from "../types";

function statusOf(v: Venue): "passed" | "failed" | "empty" {
  const low = v.status.trim().toLocaleLowerCase("ru");
  if (low === "прошел") return "passed";
  if (low === "не прошел") return "failed";
  return "empty";
}

function statusLabel(kind: ReturnType<typeof statusOf>): string {
  if (kind === "passed") return "Прошел";
  if (kind === "failed") return "Не прошел";
  return "не задан";
}

export function StatsScreen({
  version,
  onOpen,
}: {
  version: number;
  onOpen: (v: Venue) => void;
}) {
  const [items, setItems] = useState<Venue[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setItems(null);
    api
      .venues("all")
      .then((r) => !cancelled && setItems(r.items))
      .catch((e: ApiError) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [version, reload]);

  const summary = useMemo(() => {
    const list = items ?? [];
    let passed = 0;
    let failed = 0;
    let empty = 0;
    let withAroma = 0;
    let withFormat = 0;
    for (const v of list) {
      const k = statusOf(v);
      if (k === "passed") passed += 1;
      else if (k === "failed") failed += 1;
      else empty += 1;
      if (v.aroma.trim()) withAroma += 1;
      if (v.format.trim()) withFormat += 1;
    }
    return { total: list.length, passed, failed, empty, withAroma, withFormat };
  }, [items]);

  return (
    <div className="page">
      <h1 className="title">Статистика</h1>

      {error && (
        <div className="banner error">
          {error}{" "}
          <button className="text-button" onClick={() => setReload((r) => r + 1)}>
            Повторить
          </button>
        </div>
      )}

      {!error && items === null && (
        <div className="center-pad">
          <div className="spinner" />
        </div>
      )}

      {items && (
        <>
          <div className="stats-summary">
            <div className="stats-pill">
              <span className="stats-num">{summary.total}</span>
              <span className="stats-cap">всего</span>
            </div>
            <div className="stats-pill ok">
              <span className="stats-num">{summary.passed}</span>
              <span className="stats-cap">прошел</span>
            </div>
            <div className="stats-pill bad">
              <span className="stats-num">{summary.failed}</span>
              <span className="stats-cap">не прошел</span>
            </div>
            <div className="stats-pill">
              <span className="stats-num">{summary.empty}</span>
              <span className="stats-cap">без статуса</span>
            </div>
          </div>

          <p className="hint">
            С ароматами: {summary.withAroma} · с форматом: {summary.withFormat}
          </p>

          {items.length === 0 ? (
            <div className="empty">
              <p>Нет заведений</p>
            </div>
          ) : (
            <div className="venue-stats">
              {items.map((v) => {
                const kind = statusOf(v);
                return (
                  <button
                    key={v.row}
                    className="venue-stat-card"
                    onClick={() => {
                      haptic.select();
                      onOpen(v);
                    }}
                  >
                    <div className="venue-stat-top">
                      <span className="list-title">{v.name}</span>
                      <span className={`status-badge ${kind}`}>{statusLabel(kind)}</span>
                    </div>
                    <div className="venue-stat-meta">
                      <span>Ароматы: {v.aroma.trim() ? v.aroma : "—"}</span>
                      <span>Формат: {v.format.trim() ? v.format : "—"}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
