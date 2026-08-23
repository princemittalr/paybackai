interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: 'green' | 'red' | 'blue' | 'yellow' | 'gray';
  icon: string;
}

const colorMap = {
  green: 'bg-green-50 border-green-200 text-green-700',
  red: 'bg-red-50 border-red-200 text-red-700',
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
  gray: 'bg-gray-50 border-gray-200 text-gray-700',
};

export default function StatCard({ title, value, subtitle, color = 'gray', icon }: StatCardProps) {
  return (
    <div className={`rounded-xl border-2 p-5 ${colorMap[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        <span className="text-xs font-medium uppercase tracking-wide opacity-70">{title}</span>
      </div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {subtitle && <div className="text-sm mt-1 opacity-70">{subtitle}</div>}
    </div>
  );
}