export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (error) {
    if (error instanceof TypeError) throw new Error("API недоступен. Запустите backend на порту 8000.");
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail ?? "Не удалось выполнить запрос") as Error & { code?: string };
    error.code = body.code; // stable machine-readable code from the backend (Track E2)
    throw error;
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
