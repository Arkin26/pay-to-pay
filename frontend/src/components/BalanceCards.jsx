export function paiseToInr(paise) {
  const n = Number(paise || 0);
  return (n / 100).toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  });
}

export default function BalanceCards({ me }) {
  const available = me?.available_balance ?? 0;
  const held = me?.held_balance ?? 0;
  const paid = me?.total_paid_out ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div className="rounded-lg border border-playto-border bg-playto-bg1 p-4">
        <div className="text-sm text-playto-muted">Available Balance</div>
        <div className="mt-2 text-2xl font-semibold text-white">{paiseToInr(available)}</div>
      </div>
      <div className="rounded-lg border border-playto-border bg-playto-bg1 p-4">
        <div className="text-sm text-playto-muted">Held Balance</div>
        <div className="mt-2 text-2xl font-semibold text-playto-muted">{paiseToInr(held)}</div>
      </div>
      <div className="rounded-lg border border-playto-border bg-playto-bg1 p-4">
        <div className="text-sm text-playto-muted">Total Paid Out</div>
        <div className="mt-2 text-2xl font-semibold text-white">{paiseToInr(paid)}</div>
      </div>
    </div>
  );
}
