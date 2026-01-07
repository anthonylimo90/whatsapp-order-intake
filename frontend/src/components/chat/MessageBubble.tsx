import { Mic } from 'lucide-react';
import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isCustomer = message.role === 'customer';
  const isSystem = message.role === 'system';
  const isVoiceNote = message.message_type === 'voice_transcription';

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
      <div className="flex justify-center my-2">
        <div className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1 rounded-full">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isCustomer ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={`message-bubble ${isCustomer ? 'outgoing' : 'incoming'}`}
      >
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
        <p className="text-sm text-gray-800 whitespace-pre-wrap">{message.content}</p>
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
      </div>
    </div>
  );
}
