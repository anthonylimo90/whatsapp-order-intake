import { useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import {
  Package,
  Clock,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  ArrowLeft
} from 'lucide-react';

export function DashboardPage() {
  const { metrics, confidenceDistribution, loadMetrics } = useChatStore();

  useEffect(() => {
    loadMetrics();
    // Refresh metrics every 30 seconds
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, [loadMetrics]);

  const MetricCard = ({
    title,
    value,
    subtitle,
    icon: Icon,
    color
  }: {
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ElementType;
    color: string;
  }) => (
    <div className="bg-white rounded-xl border p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
      <p className="text-sm text-gray-600 mt-1">{title}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a
              href="/"
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </a>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Dashboard</h1>
              <p className="text-sm text-gray-500">Order processing metrics</p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {!metrics ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-3 border-green-500 border-t-transparent rounded-full mx-auto mb-3"></div>
            <p className="text-gray-500">Loading metrics...</p>
          </div>
        ) : (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <MetricCard
                title="Total Orders"
                value={metrics.total_orders}
                subtitle={`${metrics.orders_today} today`}
                icon={Package}
                color="bg-blue-500"
              />
              <MetricCard
                title="Auto-Processed"
                value={`${metrics.auto_process_rate}%`}
                subtitle={`${metrics.auto_processed_count} orders`}
                icon={CheckCircle}
                color="bg-green-500"
              />
              <MetricCard
                title="Review Queue"
                value={metrics.review_queue_count}
                subtitle="Awaiting review"
                icon={Clock}
                color="bg-yellow-500"
              />
              <MetricCard
                title="Manual Required"
                value={metrics.manual_count}
                subtitle="Low confidence"
                icon={AlertTriangle}
                color="bg-red-500"
              />
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-xl border p-6">
                <h3 className="font-semibold text-gray-800 mb-4">Average Confidence</h3>
                <div className="flex items-end gap-4">
                  <p className="text-4xl font-bold text-gray-800">
                    {(metrics.average_confidence * 100).toFixed(0)}%
                  </p>
                  <div className="h-2 flex-1 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${metrics.average_confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border p-6">
                <h3 className="font-semibold text-gray-800 mb-4">Avg Processing Time</h3>
                <p className="text-4xl font-bold text-gray-800">
                  {(metrics.average_processing_time_ms / 1000).toFixed(1)}s
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  vs 3 min manual processing
                </p>
              </div>

              <div className="bg-white rounded-xl border p-6">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-500" />
                  Time Saved
                </h3>
                <p className="text-4xl font-bold text-green-600">
                  {metrics.total_time_saved_minutes.toFixed(0)} min
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Total automation savings
                </p>
              </div>
            </div>

            {/* Confidence Distribution */}
            {confidenceDistribution && (
              <div className="bg-white rounded-xl border p-6">
                <h3 className="font-semibold text-gray-800 mb-4">Confidence Distribution</h3>
                <div className="flex gap-8">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-4 h-4 rounded bg-green-500" />
                      <span className="text-sm text-gray-600">High Confidence</span>
                      <span className="ml-auto font-semibold">{confidenceDistribution.high}</span>
                    </div>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-4 h-4 rounded bg-yellow-500" />
                      <span className="text-sm text-gray-600">Medium Confidence</span>
                      <span className="ml-auto font-semibold">{confidenceDistribution.medium}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 rounded bg-red-500" />
                      <span className="text-sm text-gray-600">Low Confidence</span>
                      <span className="ml-auto font-semibold">{confidenceDistribution.low}</span>
                    </div>
                  </div>
                  <div className="w-48 h-32 flex items-end gap-2">
                    {['high', 'medium', 'low'].map((level) => {
                      const total = confidenceDistribution.high + confidenceDistribution.medium + confidenceDistribution.low;
                      const value = confidenceDistribution[level as keyof typeof confidenceDistribution];
                      const height = total > 0 ? (value / total) * 100 : 0;
                      const colors = { high: 'bg-green-500', medium: 'bg-yellow-500', low: 'bg-red-500' };
                      return (
                        <div
                          key={level}
                          className={`flex-1 ${colors[level as keyof typeof colors]} rounded-t transition-all`}
                          style={{ height: `${Math.max(height, 5)}%` }}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
