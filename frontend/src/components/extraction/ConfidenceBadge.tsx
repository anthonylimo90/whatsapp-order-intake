interface ConfidenceBadgeProps {
  level: 'high' | 'medium' | 'low';
  size?: 'sm' | 'md';
}

const levelConfig = {
  high: {
    bg: 'bg-green-500',
    text: 'HIGH',
    icon: '🟢',
  },
  medium: {
    bg: 'bg-yellow-500',
    text: 'MEDIUM',
    icon: '🟡',
  },
  low: {
    bg: 'bg-red-500',
    text: 'LOW',
    icon: '🔴',
  },
};

export function ConfidenceBadge({ level, size = 'sm' }: ConfidenceBadgeProps) {
  const config = levelConfig[level];
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span
      className={`${config.bg} text-white font-medium rounded-full ${sizeClasses}`}
    >
      {config.icon} {config.text}
    </span>
  );
}
