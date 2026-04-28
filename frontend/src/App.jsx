import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchMe, fetchPayouts } from "./api.js";
import BalanceCards from "./components/BalanceCards.jsx";
import LedgerFeed from "./components/LedgerFeed.jsx";
import PayoutForm from "./components/PayoutForm.jsx";
import PayoutTable from "./components/PayoutTable.jsx";

export default function App() {
  const [tokenInput, setTokenInput] = useState(
    () => localStorage.getItem("playto_token") || ""
  );
  const [me, setMe] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [error, setError] = useState("");

  const saveToken = useCallback(() => {
    localStorage.setItem("playto_token", tokenInput.trim());
    window.location.reload();
  }, [tokenInput]);

  const load = useCallback(async () => {
    setError("");
    try {
      const [m, ps] = await Promise.all([fetchMe(), fetchPayouts()]);
      setMe(m);
      setPayouts(Array.isArray(ps) ? ps : ps?.results || []);
    } catch (e) {
      setError(String(e?.message || e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => {
      fetchPayouts()
        .then((ps) => setPayouts(Array.isArray(ps) ? ps : ps?.results || []))
        .catch(() => {});
    }, 5000);
    return () => window.clearInterval(id);
  }, []);

  const bankAccounts = useMemo(() => me?.bank_accounts || [], [me]);

  return (
    <div className="min-h-screen bg-playto-bg0 text-white">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-playto-border bg-playto-bg1 md:block">
          <div className="p-4">
            <div className="text-xs text-playto-muted">Merchant</div>
            <div className="mt-1 text-lg font-semibold text-white">{me?.name || "—"}</div>
            <div className="mt-1 text-xs text-playto-muted">{me?.email || ""}</div>
          </div>
          <div className="border-t border-playto-border p-4">
            <div className="text-xs text-playto-muted">API token</div>
            <textarea
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              className="mt-2 h-24 w-full resize-none rounded-md border border-playto-border bg-playto-bg0 p-2 text-xs text-white"
              placeholder="Paste DRF token (from seed output)"
            />
            <button
              type="button"
              onClick={saveToken}
              className="mt-2 w-full rounded-md border border-playto-border bg-playto-bg2 px-3 py-2 text-xs text-white hover:border-playto-orange"
            >
              Save token &amp; reload
            </button>
          </div>
        </aside>

        <main className="flex-1 p-4 md:p-8">
          <div className="mx-auto max-w-6xl space-y-6">
            <div className="md:hidden">
              <div className="text-xs text-playto-muted">Merchant</div>
              <div className="text-xl font-semibold">{me?.name || "—"}</div>
            </div>

            {error ? (
              <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                {error}
              </div>
            ) : null}

            <BalanceCards me={me} />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <LedgerFeed entries={me?.recent_ledger_entries} />
              <PayoutForm me={me} bankAccounts={bankAccounts} onSuccess={load} />
            </div>

            <PayoutTable payouts={payouts} />
          </div>
        </main>
      </div>
    </div>
  );
}
