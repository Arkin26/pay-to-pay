const API_BASE = import.meta.env.VITE_API_BASE || "";

function normalizeToken(raw) {
  if (!raw) return "";
  let t = String(raw).trim();
  if (!t) return "";

  // Allow pasting "token=...." or whole seed output line.
  // Examples:
  // - "token=abc123"
  // - "Acme Store: username=... token=abc123 total_credits_paise=..."
  const m = t.match(/\btoken=([0-9a-f]{20,})\b/i);
  if (m?.[1]) t = m[1];

  // If user pastes "Token abc..." or "Authorization: Token abc..."
  t = t.replace(/^Authorization:\s*/i, "").trim();
  t = t.replace(/^Token\s+/i, "").trim();

  return t;
}

export function authHeaders() {
  const token =
    import.meta.env.VITE_AUTH_TOKEN || localStorage.getItem("playto_token");
  const h = { "Content-Type": "application/json" };
  const normalized = normalizeToken(token);
  if (normalized) h.Authorization = `Token ${normalized}`;
  return h;
}

export async function fetchMe() {
  const r = await fetch(`${API_BASE}/api/v1/merchants/me/`, {
    headers: authHeaders(),
  });
  if (!r.ok) throw new Error(`me failed: ${r.status}`);
  return r.json();
}

export async function fetchPayouts() {
  const r = await fetch(`${API_BASE}/api/v1/payouts/`, { headers: authHeaders() });
  if (!r.ok) throw new Error(`payouts failed: ${r.status}`);
  return r.json();
}

export async function createPayout({ amountPaise, bankAccountId, idempotencyKey }) {
  const r = await fetch(`${API_BASE}/api/v1/payouts/`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({
      amount_paise: amountPaise,
      bank_account_id: bankAccountId,
    }),
  });
  const text = await r.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { detail: text };
  }
  return { ok: r.ok, status: r.status, body };
}
