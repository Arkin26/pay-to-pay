import { paiseToInr } from "./BalanceCards.jsx";

function Badge({ type }) {
  const isCredit = type === "credit";
  return (
    <span
      className={
        isCredit
          ? "rounded-full bg-playto-orange/15 px-2 py-0.5 text-xs font-medium text-playto-orange"
          : "rounded-full bg-playto-bg2 px-2 py-0.5 text-xs font-medium text-playto-muted"
      }
    >
      {type}
    </span>
  );
}

export default function LedgerFeed({ entries }) {
  return (
    <div className="rounded-lg border border-playto-border bg-playto-bg1">
      <div className="border-b border-playto-border px-4 py-3 text-sm font-medium text-playto-muted">
        Credits &amp; Debits
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-playto-muted">
            <tr className="border-b border-playto-border">
              <th className="px-4 py-2 font-medium">Date</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Amount</th>
              <th className="px-4 py-2 font-medium">Reference</th>
            </tr>
          </thead>
          <tbody>
            {(entries || []).map((e) => {
              const isCredit = e.entry_type === "credit";
              return (
                <tr key={e.id} className="border-b border-playto-border/60">
                  <td className="px-4 py-2 text-playto-muted">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <Badge type={e.entry_type} />
                  </td>
                  <td
                    className={
                      isCredit ? "px-4 py-2 text-playto-orange" : "px-4 py-2 text-playto-muted"
                    }
                  >
                    {paiseToInr(e.amount_paise)}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-playto-muted">{e.reference_id}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
