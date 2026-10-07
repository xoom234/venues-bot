import { insideTelegram, useDevButtons } from "../tg";

/** Замена MainButton / BackButton в обычном браузере. */
export function DevButtons() {
  const { main, back } = useDevButtons();
  if (insideTelegram) return null;
  if (!main && !back) return null;

  return (
    <div className="dev-buttons">
      {back && (
        <button className="dev-back" onClick={back}>
          ← Назад
        </button>
      )}
      {main && (
        <button
          className="primary"
          disabled={!main.enabled || main.loading}
          onClick={main.onClick}
        >
          {main.loading ? "…" : main.text}
        </button>
      )}
    </div>
  );
}
