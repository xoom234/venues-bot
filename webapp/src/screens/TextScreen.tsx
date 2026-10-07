import { useState } from "react";
import { api, ApiError } from "../api";
import { haptic, useMainButton } from "../tg";
import type { Venue } from "../types";

export function TextScreen({
  venue,
  mode,
  onSaved,
}: {
  venue: Venue;
  mode: "aroma" | "format";
  onSaved: (v: Venue) => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title = mode === "aroma" ? "Добавить аромат" : "Изменить формат";
  const placeholder = mode === "aroma" ? "манго, мята" : "день рождения";
  const button = mode === "aroma" ? "Добавить" : "Сохранить";

  const submit = async () => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      const patch =
        mode === "aroma" ? { aroma_append: trimmed } : { format: trimmed };
      const updated = await api.update(venue.row, patch);
      haptic.success();
      onSaved(updated);
    } catch (e) {
      haptic.error();
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  useMainButton({
    text: button,
    visible: true,
    enabled: text.trim().length > 0,
    loading: busy,
    onClick: submit,
  });

  return (
    <div className="page">
      <h1 className="title">{title}</h1>
      <p className="subtitle">{venue.name}</p>
      {mode === "aroma" && venue.aroma && (
        <p className="hint">Сейчас: {venue.aroma}</p>
      )}
      {mode === "format" && venue.format && (
        <p className="hint">Сейчас: {venue.format}</p>
      )}
      <label className="input-block">
        <span className="label">Текст</span>
        <input
          autoFocus
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit();
          }}
        />
      </label>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}
