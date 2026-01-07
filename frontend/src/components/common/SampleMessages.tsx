import { useEffect } from 'react';
import { useChatStore } from '../../store/chatStore';
import { MessageSquare, Globe } from 'lucide-react';

interface SampleMessagesProps {
  onSelect: (message: string) => void;
}

export function SampleMessages({ onSelect }: SampleMessagesProps) {
  const { sampleMessages, loadSampleMessages, resetChat } = useChatStore();

  useEffect(() => {
    loadSampleMessages();
  }, [loadSampleMessages]);

  const handleSelect = (message: string) => {
    resetChat();
    onSelect(message);
  };

  const confidenceColors = {
    high: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-red-100 text-red-700',
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="bg-gray-50 px-4 py-3 border-b sticky top-0">
        <h3 className="font-semibold text-gray-800">Sample Messages</h3>
        <p className="text-xs text-gray-500 mt-1">Click to try these scenarios</p>
      </div>

      <div className="p-4 space-y-3">
        {sampleMessages.map((sample) => (
          <button
            key={sample.id}
            onClick={() => handleSelect(sample.message)}
            className="w-full text-left bg-white rounded-lg border p-3 hover:border-green-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-gray-400" />
                <span className="font-medium text-sm text-gray-800">{sample.name}</span>
              </div>
              <div className="flex items-center gap-2">
                {sample.language !== 'english' && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    {sample.language}
                  </span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full ${confidenceColors[sample.expected_confidence as keyof typeof confidenceColors]}`}>
                  {sample.expected_confidence}
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mb-2">{sample.description}</p>
            <p className="text-xs text-gray-400 line-clamp-2 italic">
              "{sample.message.substring(0, 100)}..."
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
