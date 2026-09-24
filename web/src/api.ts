export type Session = {user: string; csrf: string; manager?: boolean};
let csrf = '';
export function setCsrf(value: string) { csrf = value; }
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: body === undefined ? {} : {'Content-Type':'application/json','X-CSRF-TOKEN':csrf},
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    let detail = response.status === 401 ? 'Please sign in again.' : response.status === 403 ? 'This account cannot make that change. Try refreshing the page.' : 'The request failed. Please try again.';
    try { const data = await response.json(); if (typeof data.detail === 'string') detail = data.detail; else if (Array.isArray(data.detail)) detail = 'Check the fields and try again.'; } catch {}
    throw new Error(detail);
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
export async function login(username: string, password: string): Promise<Session> {
  const session = await api<Session>('/login', {username,password});
  setCsrf(session.csrf);
  return session;
}
export const date = (value: string | null) => value ? new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : 'Not yet';
