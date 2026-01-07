import { useState } from 'react';
import { useChatStore } from '../../store/chatStore';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Package, User, Calendar, AlertTriangle, CheckCircle, Clock, ArrowRight, History, Layers, Plus, Edit3 } from 'lucide-react';
import type { CumulativeState, Changes, OrderSnapshot, ExtractionResult, Order } from '../../types';

type ViewMode = 'cumulative' | 'latest' | 'history';

export function ExtractionPanel() {
  const {
    currentExtraction,
    currentOrder,
    routingDecision,
    isProcessing,
    cumulativeState,
    snapshots,
    latestChanges,
  } = useChatStore();

  const [viewMode, setViewMode] = useState<ViewMode>('cumulative');

  // Show cumulative if available, otherwise latest
  const hasCumulativeData = cumulativeState && cumulativeState.items.length > 0;
  const hasExtractionData = currentExtraction !== null;

  if (!hasCumulativeData && !hasExtractionData && !isProcessing) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 p-6">
        <div className="text-center">
          <Package className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Send an order message to see extraction results</p>
        </div>
      </div>
    );
  }

  if (isProcessing) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-3 border-green-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-gray-600">Extracting order details...</p>
        </div>
      </div>
    );
  }

  const routingColors = {
    auto_process: 'bg-green-100 text-green-800 border-green-200',
    review: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    manual: 'bg-red-100 text-red-800 border-red-200',
  };

  const routingLabels = {
    auto_process: 'Auto-Process',
    review: 'Review Queue',
    manual: 'Manual Review',
  };

  const routingIcons = {
    auto_process: <CheckCircle className="w-4 h-4" />,
    review: <Clock className="w-4 h-4" />,
    manual: <AlertTriangle className="w-4 h-4" />,
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Header */}
      <div className="flex border-b bg-gray-50">
        <button
          onClick={() => setViewMode('cumulative')}
          className={`flex-1 px-3 py-2 text-sm font-medium flex items-center justify-center gap-1.5 transition-colors ${
            viewMode === 'cumulative'
              ? 'text-green-600 border-b-2 border-green-600 bg-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Layers className="w-4 h-4" />
          Cumulative
          {cumulativeState && (
            <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
              {cumulativeState.items.filter(i => i.is_active).length}
            </span>
          )}
        </button>
        <button
          onClick={() => setViewMode('latest')}
          className={`flex-1 px-3 py-2 text-sm font-medium flex items-center justify-center gap-1.5 transition-colors ${
            viewMode === 'latest'
              ? 'text-green-600 border-b-2 border-green-600 bg-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Package className="w-4 h-4" />
          Latest
        </button>
        <button
          onClick={() => setViewMode('history')}
          className={`flex-1 px-3 py-2 text-sm font-medium flex items-center justify-center gap-1.5 transition-colors ${
            viewMode === 'history'
              ? 'text-green-600 border-b-2 border-green-600 bg-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <History className="w-4 h-4" />
          History
          {snapshots.length > 0 && (
            <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
              {snapshots.length}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {viewMode === 'cumulative' && (
          <CumulativeView
            cumulativeState={cumulativeState}
            latestChanges={latestChanges}
            routingDecision={routingDecision}
            routingColors={routingColors}
            routingLabels={routingLabels}
            routingIcons={routingIcons}
          />
        )}

        {viewMode === 'latest' && currentExtraction && (
          <LatestExtractionView
            extraction={currentExtraction}
            order={currentOrder}
            routingDecision={routingDecision}
            routingColors={routingColors}
            routingLabels={routingLabels}
            routingIcons={routingIcons}
          />
        )}

        {viewMode === 'history' && (
          <HistoryView snapshots={snapshots} />
        )}
      </div>
    </div>
  );
}

// Cumulative View Component
function CumulativeView({
  cumulativeState,
  latestChanges,
  routingDecision,
  routingColors,
  routingLabels,
  routingIcons,
}: {
  cumulativeState: CumulativeState | null;
  latestChanges: Changes | null;
  routingDecision: string | null;
  routingColors: Record<string, string>;
  routingLabels: Record<string, string>;
  routingIcons: Record<string, React.ReactNode>;
}) {
  if (!cumulativeState) {
    return (
      <div className="p-6 text-center text-gray-500">
        <Layers className="w-10 h-10 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No cumulative order data yet</p>
      </div>
    );
  }

  const activeItems = cumulativeState.items.filter(i => i.is_active);
  const addedNames = new Set(latestChanges?.added.map(a => a.product_name) || []);
  const modifiedNames = new Set(latestChanges?.modified.map(m => m.product_name) || []);

  // Check if an item needs clarification based on pending_clarifications
  const itemNeedsClarification = (productName: string): string | null => {
    if (!cumulativeState.pending_clarifications?.length) return null;
    const match = cumulativeState.pending_clarifications.find(
      c => c.toLowerCase().includes(productName.toLowerCase())
    );
    return match || null;
  };

  return (
    <div className="p-4 space-y-4">
      {/* Summary Header */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-600">Overall Confidence</span>
          <ConfidenceBadge level={cumulativeState.overall_confidence} size="md" />
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <span>Version {cumulativeState.version}</span>
          <span className="text-gray-300">•</span>
          <span>{activeItems.length} items</span>
        </div>

        {routingDecision && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${routingColors[routingDecision as keyof typeof routingColors]}`}>
            {routingIcons[routingDecision as keyof typeof routingIcons]}
            <span className="text-sm font-medium">
              {routingLabels[routingDecision as keyof typeof routingLabels]}
            </span>
            <ArrowRight className="w-4 h-4 ml-auto" />
          </div>
        )}
      </div>

      {/* Customer Info */}
      {(cumulativeState.customer_name || cumulativeState.customer_organization) && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center gap-2 mb-2">
            <User className="w-4 h-4 text-gray-400" />
            <h4 className="font-medium text-gray-800">Customer</h4>
          </div>
          <p className="text-sm text-gray-800">{cumulativeState.customer_name}</p>
          {cumulativeState.customer_organization && (
            <p className="text-sm text-gray-500">{cumulativeState.customer_organization}</p>
          )}
        </div>
      )}

      {/* Delivery Info */}
      {(cumulativeState.delivery_date || cumulativeState.urgency) && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <h4 className="font-medium text-gray-800">Delivery</h4>
          </div>
          {cumulativeState.delivery_date && (
            <p className="text-sm text-gray-800">{cumulativeState.delivery_date}</p>
          )}
          {cumulativeState.urgency && (
            <p className="text-sm text-orange-600 font-medium">{cumulativeState.urgency}</p>
          )}
        </div>
      )}

      {/* Cumulative Items */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Package className="w-4 h-4 text-gray-400" />
          <h4 className="font-medium text-gray-800">
            Order Items ({activeItems.length})
          </h4>
        </div>
        <div className="space-y-2">
          {activeItems.map((item, index) => {
            const isAdded = addedNames.has(item.product_name);
            const isModified = modifiedNames.has(item.product_name);
            const clarificationReason = itemNeedsClarification(item.product_name);
            const needsClarification = !!clarificationReason;

            return (
              <div
                key={index}
                className={`p-3 rounded-lg border transition-colors ${
                  needsClarification
                    ? 'bg-amber-50 border-amber-300 clarification-item'
                    : isAdded
                    ? 'bg-green-50 border-green-200'
                    : isModified
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {needsClarification && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                    {!needsClarification && isAdded && <Plus className="w-4 h-4 text-green-600" />}
                    {!needsClarification && isModified && <Edit3 className="w-4 h-4 text-blue-600" />}
                    <span className="font-medium text-gray-800">{item.product_name}</span>
                  </div>
                  <ConfidenceBadge level={item.confidence} />
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {item.quantity} {item.unit}
                  </span>
                  {item.modification_count > 0 && (
                    <span className="text-xs text-gray-400">
                      Modified {item.modification_count}x
                    </span>
                  )}
                </div>
                {needsClarification && (
                  <p className="text-xs text-amber-700 mt-2 bg-amber-100 px-2 py-1 rounded">
                    Needs clarification
                  </p>
                )}
                {item.notes && !needsClarification && (
                  <p className="text-xs text-amber-600 mt-1">⚠️ {item.notes}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Pending Clarifications */}
      {cumulativeState.requires_clarification && cumulativeState.pending_clarifications.length > 0 && (
        <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h4 className="font-medium text-amber-800">Clarification Needed</h4>
          </div>
          <ul className="space-y-2">
            {cumulativeState.pending_clarifications.map((item, index) => (
              <li key={index} className="text-sm text-amber-700 flex items-start gap-2">
                <span className="text-amber-500">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Latest Extraction View Component
function LatestExtractionView({
  extraction,
  order,
  routingDecision,
  routingColors,
  routingLabels,
  routingIcons,
}: {
  extraction: ExtractionResult;
  order: Order | null;
  routingDecision: string | null;
  routingColors: Record<string, string>;
  routingLabels: Record<string, string>;
  routingIcons: Record<string, React.ReactNode>;
}) {
  return (
    <div className="p-4 space-y-4">
      {/* Overall Confidence & Routing */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-600">Overall Confidence</span>
          <ConfidenceBadge level={extraction.overall_confidence} size="md" />
        </div>

        {routingDecision && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${routingColors[routingDecision as keyof typeof routingColors]}`}>
            {routingIcons[routingDecision as keyof typeof routingIcons]}
            <span className="text-sm font-medium">
              {routingLabels[routingDecision as keyof typeof routingLabels]}
            </span>
            <ArrowRight className="w-4 h-4 ml-auto" />
          </div>
        )}

        {order && (
          <div className="mt-3 text-xs text-gray-500">
            Processing time: {order.processing_time_ms}ms
          </div>
        )}
      </div>

      {/* Customer Info */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-3">
          <User className="w-4 h-4 text-gray-400" />
          <h4 className="font-medium text-gray-800">Customer</h4>
        </div>
        <div className="space-y-1">
          <p className="text-sm text-gray-800">{extraction.customer_name}</p>
          {extraction.customer_organization && (
            <p className="text-sm text-gray-500">{extraction.customer_organization}</p>
          )}
        </div>
      </div>

      {/* Delivery Info */}
      {(extraction.requested_delivery_date || extraction.delivery_urgency) && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-4 h-4 text-gray-400" />
            <h4 className="font-medium text-gray-800">Delivery</h4>
          </div>
          <div className="space-y-1">
            {extraction.requested_delivery_date && (
              <p className="text-sm text-gray-800">{extraction.requested_delivery_date}</p>
            )}
            {extraction.delivery_urgency && (
              <p className="text-sm text-orange-600 font-medium">
                {extraction.delivery_urgency}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Extracted Items */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Package className="w-4 h-4 text-gray-400" />
          <h4 className="font-medium text-gray-800">
            Items ({extraction.items.length})
          </h4>
        </div>
        <div className="space-y-3">
          {extraction.items.map((item, index) => (
            <div key={index} className="border-b last:border-0 pb-3 last:pb-0">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    {item.product_name}
                  </p>
                  <p className="text-sm text-gray-600">
                    {item.quantity} {item.unit}
                  </p>
                  {item.notes && (
                    <p className="text-xs text-amber-600 mt-1">
                      ⚠️ {item.notes}
                    </p>
                  )}
                </div>
                <ConfidenceBadge level={item.confidence} />
              </div>
              <p className="text-xs text-gray-400 mt-1 italic">
                "{item.original_text}"
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Clarification Needed */}
      {extraction.requires_clarification && extraction.clarification_needed.length > 0 && (
        <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h4 className="font-medium text-amber-800">Clarification Needed</h4>
          </div>
          <ul className="space-y-2">
            {extraction.clarification_needed.map((item, index) => (
              <li key={index} className="text-sm text-amber-700 flex items-start gap-2">
                <span className="text-amber-500">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// History View Component
function HistoryView({ snapshots }: { snapshots: OrderSnapshot[] }) {
  if (snapshots.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500">
        <History className="w-10 h-10 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No extraction history yet</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="space-y-4">
        {snapshots.slice().reverse().map((snapshot) => (
          <div key={snapshot.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-medium">
                  v{snapshot.version}
                </div>
                <span className="text-sm text-gray-600">
                  {new Date(snapshot.created_at).toLocaleTimeString()}
                </span>
              </div>
              {snapshot.extraction_confidence && (
                <ConfidenceBadge level={snapshot.extraction_confidence as 'high' | 'medium' | 'low'} />
              )}
            </div>

            {/* Changes Summary */}
            {snapshot.changes && (
              <div className="flex flex-wrap gap-2 mb-3">
                {snapshot.changes.added.length > 0 && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    +{snapshot.changes.added.length} added
                  </span>
                )}
                {snapshot.changes.modified.length > 0 && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                    {snapshot.changes.modified.length} modified
                  </span>
                )}
                {snapshot.changes.unchanged.length > 0 && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {snapshot.changes.unchanged.length} unchanged
                  </span>
                )}
              </div>
            )}

            {/* Items */}
            <div className="text-sm text-gray-600">
              <p className="font-medium mb-1">{snapshot.items.length} items:</p>
              <div className="text-xs space-y-1">
                {snapshot.items.slice(0, 5).map((item, i) => (
                  <div key={i} className="flex justify-between">
                    <span>{item.product_name}</span>
                    <span className="text-gray-400">{item.quantity} {item.unit}</span>
                  </div>
                ))}
                {snapshot.items.length > 5 && (
                  <p className="text-gray-400 italic">
                    +{snapshot.items.length - 5} more items
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
