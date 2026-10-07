import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { haptic } from "../tg";
import type { Filter, Venue } from "../types";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "passed", label: "Прошел" },
  { id: "failed", label: "Не прошел" },
];

function statusLabel(status: string): string {
  return status || "не задан";
}

export function ListScreen({
  version,
  onOpen,
  onAdd,
}: {
  version: number;
  onOpen: (v: Venue) => void;
  onAdd: () => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Venue[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setItems(null);
    api
      .venues(filter)
      .then((r) => !cancelled && setItems(r.items))
      .catch((e: ApiError) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [filter, version, reload]);

  const shown = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("ru");
    if (!q || !items) return items ?? [];
    return items.filter((v) => v.name.toLocaleLowerCase("ru").includes(q));
  }, [items, query]);

  return (
    <div className="page">
      <div className="toolbar">
        <div className="search">
          <input
            type="search"
            placeholder="Название"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button
          className="chip accent"
          onClick={() => {
            haptic.select();
            onAdd();
          }}
        >
          + Добавить
        </button>
      </div>

      <div className="chips">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            className={`chip ${filter === f.id ? "selected" : ""}`}
            onClick={() => {
              haptic.select();
              setFilter(f.id);
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

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

      {!error && items && shown.length === 0 && (
        <div className="empty">
          <p>Нет заведений</p>
        </div>
      )}

      {shown.length > 0 && (
        <div className="list">
          {shown.map((v) => (
            <button
              key={v.row}
              className="list-row"
              onClick={() => {
                haptic.select();
                onOpen(v);
              }}
            >
              <span className="list-title">{v.name}</span>
              <span className="list-meta">{statusLabel(v.status)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
