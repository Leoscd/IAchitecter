interface BudgetCardProps {
  reply: string;
}

export function BudgetCard({ reply }: BudgetCardProps) {
  // Busca formato de presupuesto: $X.XXX.XXX o similar
  const budgetMatch = reply.match(/\$([\d.]+)/);

  if (!budgetMatch) return null;

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-2">
      <p className="text-sm text-green-800 font-medium">Presupuesto total:</p>
      <p className="text-xl font-bold text-green-700">{budgetMatch[0]}</p>
    </div>
  );
}