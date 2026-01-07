import { useState, useRef, type KeyboardEvent } from 'react';
import { Send, Mic, Paperclip } from 'lucide-react';
import { VoiceNoteModal } from '../voice';

interface MessageInputProps {
  onSend: (message: string, messageType?: string) => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({ onSend, onFileUpload, disabled = false, placeholder = 'Type a message...' }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim(), 'text');
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleMicClick = () => {
    if (!message.trim()) {
      setShowVoiceModal(true);
    }
  };

  const handleVoiceSend = (transcription: string, messageType: string) => {
    onSend(transcription, messageType);
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onFileUpload) {
      onFileUpload(file);
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <>
      <div className="bg-[#f0f2f5] px-4 py-3 flex items-end gap-2">
        {/* Attachment button */}
        <button
          onClick={handleAttachClick}
          disabled={disabled}
          className={`w-10 h-10 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors ${disabled ? 'opacity-50' : ''}`}
          title="Attach Excel file"
        >
          <Paperclip className="w-5 h-5" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileSelect}
          className="hidden"
        />

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
          onClick={message.trim() ? handleSend : handleMicClick}
          disabled={disabled}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            message.trim() && !disabled
              ? 'bg-[#25D366] text-white hover:bg-[#128C7E]'
              : 'bg-[#25D366] text-white hover:bg-[#128C7E]'
          } ${disabled ? 'opacity-50' : ''}`}
        >
          {message.trim() ? (
            <Send className="w-5 h-5" />
          ) : (
            <Mic className="w-5 h-5" />
          )}
        </button>
      </div>

      <VoiceNoteModal
        isOpen={showVoiceModal}
        onClose={() => setShowVoiceModal(false)}
        onSend={handleVoiceSend}
      />
    </>
  );
}
