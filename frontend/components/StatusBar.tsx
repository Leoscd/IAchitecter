interface StatusBarProps {
  isLoading: boolean;
}

export function StatusBar({ isLoading }: StatusBarProps) {
  if (!isLoading) return null;

  return (
    <div className="text-sm text-gray-600 bg-gray-100 rounded px-3 py-2">
      <span className="animate-pulse">Analizando proyecto... ⚙</span>
    </div>
  );
}