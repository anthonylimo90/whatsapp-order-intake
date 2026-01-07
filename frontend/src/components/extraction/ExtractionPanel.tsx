import { useChatStore } from '../../store/chatStore';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Package, User, Calendar, AlertTriangle, CheckCircle, Clock, ArrowRight } from 'lucide-react';

export function ExtractionPanel() {
  const { currentExtraction, currentOrder, routingDecision, isProcessing } = useChatStore();

  if (!currentExtraction && !isProcessing) {
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

  if (!currentExtraction) return null;

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
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b sticky top-0">
        <h3 className="font-semibold text-gray-800">Extraction Results</h3>
      </div>

      <div className="p-4 space-y-4">
        {/* Overall Confidence & Routing */}
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-gray-600">Overall Confidence</span>
            <ConfidenceBadge level={currentExtraction.overall_confidence} size="md" />
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

          {currentOrder && (
            <div className="mt-3 text-xs text-gray-500">
              Processing time: {currentOrder.processing_time_ms}ms
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
            <p className="text-sm text-gray-800">{currentExtraction.customer_name}</p>
            {currentExtraction.customer_organization && (
              <p className="text-sm text-gray-500">{currentExtraction.customer_organization}</p>
            )}
          </div>
        </div>

        {/* Delivery Info */}
        {(currentExtraction.requested_delivery_date || currentExtraction.delivery_urgency) && (
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-gray-400" />
              <h4 className="font-medium text-gray-800">Delivery</h4>
            </div>
            <div className="space-y-1">
              {currentExtraction.requested_delivery_date && (
                <p className="text-sm text-gray-800">{currentExtraction.requested_delivery_date}</p>
              )}
              {currentExtraction.delivery_urgency && (
                <p className="text-sm text-orange-600 font-medium">
                  {currentExtraction.delivery_urgency}
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
              Items ({currentExtraction.items.length})
            </h4>
          </div>
          <div className="space-y-3">
            {currentExtraction.items.map((item, index) => (
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
        {currentExtraction.requires_clarification && currentExtraction.clarification_needed.length > 0 && (
          <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h4 className="font-medium text-amber-800">Clarification Needed</h4>
            </div>
            <ul className="space-y-2">
              {currentExtraction.clarification_needed.map((item, index) => (
                <li key={index} className="text-sm text-amber-700 flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
