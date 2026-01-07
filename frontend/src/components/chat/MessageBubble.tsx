import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isCustomer = message.role === 'customer';
  const isSystem = message.role === 'system';

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
