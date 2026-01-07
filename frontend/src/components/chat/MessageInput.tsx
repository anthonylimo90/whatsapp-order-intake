import { useState, type KeyboardEvent } from 'react';
import { Send, Mic } from 'lucide-react';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({ onSend, disabled = false, placeholder = 'Type a message...' }: MessageInputProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-[#f0f2f5] px-4 py-3 flex items-end gap-2">
      <div className="flex-1 bg-white rounded-3xl flex items-end">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 px-4 py-3 text-sm resize-none outline-none rounded-3xl max-h-32"
          style={{ minHeight: '44px' }}
        />
      </div>
      <button
        onClick={handleSend}
        disabled={disabled || !message.trim()}
        className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
          message.trim() && !disabled
            ? 'bg-[#25D366] text-white hover:bg-[#128C7E]'
            : 'bg-[#25D366] text-white opacity-50'
        }`}
      >
        {message.trim() ? (
          <Send className="w-5 h-5" />
        ) : (
          <Mic className="w-5 h-5" />
        )}
      </button>
    </div>
  );
}
