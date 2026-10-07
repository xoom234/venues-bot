import type { Filter, Venue } from "./types";
import { initData } from "./tg";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const TIMEOUT_MS = 25_000;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  let body: { error?: string };
  try {
    response = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: {
        Authorization: `tma ${initData()}`,
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    body = await response.json().catch(() => ({}));
  } catch {
    throw new ApiError(
      0,
      controller.signal.aborted
        ? "Сервер не ответил вовремя. Проверьте интернет и повторите."
        : "Нет связи с сервером. Проверьте интернет.",
    );
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    throw new ApiError(response.status, body.error || `Ошибка сервера (${response.status})`);
  }
  return body as T;
}

export const api = {
  venues: (filter: Filter = "all", q = "") => {
    const params = new URLSearchParams({ filter });
    if (q.trim()) params.set("q", q.trim());
    return request<{ items: Venue[] }>(`/api/v1/venues?${params}`);
  },
  create: (name: string) =>
    request<Venue>("/api/v1/venues", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  update: (
    row: number,
    patch: { status?: string; aroma_append?: string; format?: string },
  ) =>
    request<Venue>(`/api/v1/venues/${row}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
};
