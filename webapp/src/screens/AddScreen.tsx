import { useState } from "react";
import { api, ApiError } from "../api";
import { haptic, useMainButton } from "../tg";
import type { Venue } from "../types";

export function AddScreen({ onCreated }: { onCreated: (v: Venue) => void }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const trimmed = name.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      const venue = await api.create(trimmed);
      haptic.success();
      onCreated(venue);
    } catch (e) {
      haptic.error();
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  useMainButton({
    text: "Добавить",
    visible: true,
    enabled: name.trim().length > 0,
    loading: busy,
    onClick: submit,
  });

  return (
    <div className="page">
      <h1 className="title">Новое заведение</h1>
      <label className="input-block">
        <span className="label">Название</span>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Например, HookahPlace"
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit();
          }}
        />
      </label>
      {error && <div className="banner error">{error}</div>}
    </div>
  );
}
