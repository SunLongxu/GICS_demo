import { toNetworkError } from './networkError';

export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw toNetworkError();
  }
}

export async function apiJson<T = unknown>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  const response = await apiFetch(input, init);
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    if (!response.ok) {
      throw toNetworkError();
    }
    throw toNetworkError();
  }

  if (!response.ok) {
    throw toNetworkError();
  }

  const record = body as { status?: string };
  if (record.status === 'error') {
    throw toNetworkError();
  }

  return body as T;
}
