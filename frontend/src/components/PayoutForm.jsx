import { useEffect, useMemo, useState } from "react";
import { createPayout } from "../api.js";
import { paiseToInr } from "./BalanceCards.jsx";

function rupeesToPaise(rupeesStr) {
  const n = Number(String(rupeesStr).replace(/,/g, ""));
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.round(n * 100);
}

export default function PayoutForm({ me, bankAccounts, onSuccess }) {
  const [amountInr, setAmountInr] = useState("");
  const [bankId, setBankId] = useState(bankAccounts?.[0]?.id ?? "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!bankId && bankAccounts?.length) {
      setBankId(String(bankAccounts[0].id));
    }
  }, [bankAccounts, bankId]);

  const available = me?.available_balance ?? 0;

  const amountPaise = useMemo(() => rupeesToPaise(amountInr), [amountInr]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    if (!bankId) {
      setError("Select a bank account.");
      return;
    }
    const ap = amountPaise;
    if (ap == null) {
      setError("Enter a valid amount in ₹.");
      return;
    }
    if (ap > available) {
      setError("Insufficient funds.");
      return;
    }
    setSubmitting(true);
    try {
      const idem = crypto.randomUUID();
      const { ok, status, body } = await createPayout({
        amountPaise: ap,
        bankAccountId: Number(bankId),
        idempotencyKey: idem,
      });
      if (!ok) {
        if (status === 402) setError("Insufficient funds.");
        else setError(body?.detail || JSON.stringify(body));
        return;
      }
      setAmountInr("");
      onSuccess?.();
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-lg border border-playto-border bg-playto-bg1 p-4"
    >
      <div className="text-sm font-medium text-playto-muted">Request payout</div>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="md:col-span-1">
          <label className="text-xs text-playto-muted">Amount (₹)</label>
          <input
            value={amountInr}
            onChange={(e) => setAmountInr(e.target.value)}
            className="mt-1 w-full rounded-md border border-playto-border bg-playto-bg0 px-3 py-2 text-sm text-white outline-none focus:border-playto-orange"
            placeholder="e.g. 250.50"
          />
          {amountPaise != null ? (
            <div className="mt-1 text-xs text-playto-muted">
              Sends {amountPaise} paise ({paiseToInr(amountPaise)})
            </div>
          ) : null}
        </div>
        <div className="md:col-span-1">
          <label className="text-xs text-playto-muted">Bank account</label>
          <select
            value={bankId}
            onChange={(e) => setBankId(e.target.value)}
            className="mt-1 w-full rounded-md border border-playto-border bg-playto-bg0 px-3 py-2 text-sm text-white outline-none focus:border-playto-orange"
          >
            {(bankAccounts || []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.nickname || b.account_number} · {b.ifsc}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-playto-orange px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
          >
            {submitting ? "Submitting…" : "Submit payout"}
          </button>
        </div>
      </div>
      {error ? <div className="mt-3 text-sm text-red-400">{error}</div> : null}
    </form>
  );
}
