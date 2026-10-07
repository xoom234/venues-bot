import { useState } from "react";
import { DevButtons } from "./components/DevButtons";
import { AddScreen } from "./screens/AddScreen";
import { DetailScreen } from "./screens/DetailScreen";
import { ListScreen } from "./screens/ListScreen";
import { TextScreen } from "./screens/TextScreen";
import { insideTelegram, useBackButton } from "./tg";
import type { Screen, Venue } from "./types";

export function App() {
  const [screen, setScreen] = useState<Screen>({ name: "list" });
  const [listVersion, setListVersion] = useState(0);

  const openDetail = (venue: Venue) => setScreen({ name: "detail", venue });
  const bumpList = () => setListVersion((v) => v + 1);

  const goBack = () => {
    if (screen.name === "aroma" || screen.name === "format") {
      openDetail(screen.venue);
      return;
    }
    setScreen({ name: "list" });
  };

  useBackButton(screen.name === "list" ? null : goBack);

  return (
    <>
      <main className="screen">
        {screen.name === "list" && (
          <ListScreen
            version={listVersion}
            onOpen={openDetail}
            onAdd={() => setScreen({ name: "add" })}
          />
        )}
        {screen.name === "detail" && (
          <DetailScreen
            key={screen.venue.row}
            venue={screen.venue}
            onUpdated={(v) => {
              setScreen({ name: "detail", venue: v });
              bumpList();
            }}
            onAroma={(v) => setScreen({ name: "aroma", venue: v })}
            onFormat={(v) => setScreen({ name: "format", venue: v })}
          />
        )}
        {screen.name === "add" && (
          <AddScreen
            onCreated={(v) => {
              bumpList();
              openDetail(v);
            }}
          />
        )}
        {(screen.name === "aroma" || screen.name === "format") && (
          <TextScreen
            key={`${screen.name}-${screen.venue.row}`}
            venue={screen.venue}
            mode={screen.name}
            onSaved={(v) => {
              bumpList();
              openDetail(v);
            }}
          />
        )}
        {!insideTelegram && screen.name === "list" && (
          <p className="browser-hint">
            Откройте приложение через кнопку в боте. Для локальной отладки задайте
            VITE_DEV_INIT_DATA.
          </p>
        )}
      </main>
      <DevButtons />
    </>
  );
}
