import { useState } from 'react';
import { Mic, FileSpreadsheet, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  isFirstInGroup?: boolean;
  isLastInGroup?: boolean;
  showTimestamp?: boolean;
}

const MAX_COLLAPSED_LENGTH = 300;

export function MessageBubble({
  message,
  isFirstInGroup = true,
  isLastInGroup = true,
  showTimestamp = true
}: MessageBubbleProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const isCustomer = message.role === 'customer';
  const isSystem = message.role === 'system';
  const isVoiceNote = message.message_type === 'voice_transcription';
  const isExcelOrder = message.message_type === 'excel_order';

  // Determine if content should be collapsed
  const shouldCollapse = message.content.length > MAX_COLLAPSED_LENGTH && !isExcelOrder;
  const displayContent = shouldCollapse && !isExpanded
    ? message.content.slice(0, MAX_COLLAPSED_LENGTH)
    : message.content;
  const remainingChars = message.content.length - MAX_COLLAPSED_LENGTH;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (isSystem) {
    return (
      <div className="flex justify-center my-3">
        <div className="bg-white/90 backdrop-blur-sm text-gray-700 text-sm px-4 py-2 rounded-lg shadow-sm max-w-md">
          <p className="whitespace-pre-wrap">{displayContent}</p>
          {shouldCollapse && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-green-600 text-xs mt-2 hover:underline"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Show more (+{remainingChars} chars)
                </>
              )}
            </button>
          )}
        </div>
      </div>
    );
  }

  // Adjust margin based on grouping
  const marginClass = isFirstInGroup ? 'mt-3' : 'mt-0.5';

  return (
    <div className={`flex ${isCustomer ? 'justify-end' : 'justify-start'} ${marginClass} group`}>
      <div
        className={`message-bubble ${isCustomer ? 'outgoing' : 'incoming'} relative`}
      >
        {/* Copy button - shown on hover */}
        <button
          onClick={handleCopy}
          className="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-gray-100 rounded"
          title="Copy message"
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <Copy className="w-4 h-4 text-gray-400" />
          )}
        </button>

        {isVoiceNote && (
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-200">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <Mic className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                {/* Voice waveform visualization */}
                {[...Array(20)].map((_, i) => (
                  <div
                    key={i}
                    className="w-0.5 bg-green-600 rounded-full"
                    style={{ height: `${8 + Math.sin(i * 0.5) * 8 + Math.random() * 4}px` }}
                  />
                ))}
              </div>
            </div>
            <span className="text-xs text-gray-500">Voice Note</span>
          </div>
        )}
        {isVoiceNote && (
          <p className="text-xs text-gray-500 italic mb-1">Transcription:</p>
        )}
        {isExcelOrder && (
          <div className="flex items-center gap-3 p-2 bg-green-50 rounded-lg">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate" title={message.content.replace('📎 ', '')}>
                {message.content.replace('📎 ', '')}
              </p>
              <p className="text-xs text-gray-500">Excel Order File</p>
            </div>
          </div>
        )}
        {!isExcelOrder && (
          <>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{displayContent}</p>
            {shouldCollapse && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1 text-green-600 text-xs mt-1 hover:underline"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="w-3 h-3" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3 h-3" />
                    Show more (+{remainingChars} chars)
                  </>
                )}
              </button>
            )}
          </>
        )}
        {(showTimestamp || isLastInGroup) && (
          <div className={`flex items-center gap-1 mt-1 ${isCustomer ? 'justify-end' : 'justify-start'}`}>
            <span className="text-[10px] text-gray-500">
              {formatTime(message.created_at)}
            </span>
            {isCustomer && (
              <svg className="w-4 h-4 text-blue-500" viewBox="0 0 16 15" fill="currentColor">
                <path d="M15.01 3.316l-.478-.372a.365.365 0 0 0-.51.063L8.666 9.879a.32.32 0 0 1-.484.033l-.358-.325a.319.319 0 0 0-.484.032l-.378.483a.418.418 0 0 0 .036.541l1.32 1.266c.143.14.361.125.484-.033l6.272-8.048a.366.366 0 0 0-.064-.512zm-4.1 0l-.478-.372a.365.365 0 0 0-.51.063L4.566 9.879a.32.32 0 0 1-.484.033L1.891 7.769a.366.366 0 0 0-.515.006l-.423.433a.364.364 0 0 0 .006.514l3.258 3.185c.143.14.361.125.484-.033l6.272-8.048a.365.365 0 0 0-.063-.51z" />
              </svg>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
