import { useState } from "react";
import { api, ApiError } from "../api";
import { haptic } from "../tg";
import type { Venue } from "../types";

function show(value: string, empty = "не указано"): string {
  return value || empty;
}

export function DetailScreen({
  venue: initial,
  onUpdated,
  onAroma,
  onFormat,
}: {
  venue: Venue;
  onUpdated: (v: Venue) => void;
  onAroma: (v: Venue) => void;
  onFormat: (v: Venue) => void;
}) {
  const [venue, setVenue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setStatus = async (status: "Прошел" | "Не прошел") => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.update(venue.row, { status });
      setVenue(updated);
      onUpdated(updated);
      haptic.success();
    } catch (e) {
      haptic.error();
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <h1 className="title">{venue.name}</h1>

      <section className="card">
        <div className="field">
          <span className="label">Статус</span>
          <span className="value">{show(venue.status, "не задан")}</span>
        </div>
        <div className="field">
          <span className="label">Ароматы</span>
          <span className="value">{show(venue.aroma)}</span>
        </div>
        <div className="field">
          <span className="label">Формат</span>
          <span className="value">{show(venue.format)}</span>
        </div>
      </section>

      {error && <div className="banner error">{error}</div>}

      <div className="actions">
        <button
          className={`action pass ${venue.status === "Прошел" ? "selected" : ""}`}
          disabled={busy}
          onClick={() => setStatus("Прошел")}
        >
          Прошел
        </button>
        <button
          className={`action fail ${venue.status === "Не прошел" ? "selected" : ""}`}
          disabled={busy}
          onClick={() => setStatus("Не прошел")}
        >
          Не прошел
        </button>
        <button
          className="action"
          disabled={busy}
          onClick={() => {
            haptic.select();
            onAroma(venue);
          }}
        >
          + Аромат
        </button>
        <button
          className="action"
          disabled={busy}
          onClick={() => {
            haptic.select();
            onFormat(venue);
          }}
        >
          Изменить формат
        </button>
      </div>
    </div>
  );
}
