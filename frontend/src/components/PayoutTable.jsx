import { paiseToInr } from "./BalanceCards.jsx";

function StatusBadge({ status }) {
  const map = {
    pending: "bg-playto-bg2 text-playto-muted border-playto-border",
    processing: "bg-playto-orange/15 text-playto-orange border-playto-orange/30",
    completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    failed: "bg-red-500/10 text-red-400 border-red-500/30",
  };
  const cls = map[status] || map.pending;
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

export default function PayoutTable({ payouts }) {
  return (
    <div className="rounded-lg border border-playto-border bg-playto-bg1">
      <div className="border-b border-playto-border px-4 py-3 text-sm font-medium text-playto-muted">
        Payout history
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-playto-muted">
            <tr className="border-b border-playto-border">
              <th className="px-4 py-2 font-medium">Date</th>
              <th className="px-4 py-2 font-medium">Amount</th>
              <th className="px-4 py-2 font-medium">Bank account</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Attempts</th>
            </tr>
          </thead>
          <tbody>
            {(payouts || []).map((p) => (
              <tr key={p.id} className="border-b border-playto-border/60">
                <td className="px-4 py-2 text-playto-muted">
                  {new Date(p.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2 text-white">{paiseToInr(p.amount_paise)}</td>
                <td className="px-4 py-2 text-playto-muted">
                  {p.bank_account?.nickname || p.bank_account?.account_number}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={p.status} />
                </td>
                <td className="px-4 py-2 text-playto-muted">{p.attempts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
