import { useState, useRef, useEffect, type KeyboardEvent, type DragEvent } from 'react';
import { Send, Mic, Paperclip, FileSpreadsheet } from 'lucide-react';
import { VoiceNoteModal } from '../voice';

interface MessageInputProps {
  onSend: (message: string, messageType?: string) => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  placeholder?: string;
}

const MAX_CHARS = 2000;
const CHAR_COUNTER_THRESHOLD = 100;

export function MessageInput({ onSend, onFileUpload, disabled = false, placeholder = 'Type a message...' }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [showMultilineHint, setShowMultilineHint] = useState(false);
  const [shake, setShake] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`;
    }
  }, [message]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim(), 'text');
      setMessage('');
    } else if (!message.trim()) {
      // Shake animation for empty submit
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === 'Enter' && e.shiftKey) {
      // Show multiline hint on first Shift+Enter
      if (!localStorage.getItem('multilineHintShown')) {
        setShowMultilineHint(true);
        localStorage.setItem('multilineHintShown', 'true');
        setTimeout(() => setShowMultilineHint(false), 3000);
      }
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      onFileUpload?.(file);
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

  const charCount = message.length;
  const showCharCounter = charCount > CHAR_COUNTER_THRESHOLD;
  const isNearLimit = charCount > MAX_CHARS * 0.9;
  const isOverLimit = charCount > MAX_CHARS;

  return (
    <>
      {/* Drag overlay */}
      {isDragging && (
        <div
          className="absolute inset-0 bg-green-500/20 backdrop-blur-sm z-50 flex items-center justify-center"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="bg-white rounded-xl p-6 shadow-lg flex flex-col items-center gap-3">
            <FileSpreadsheet className="w-12 h-12 text-green-600" />
            <p className="text-gray-800 font-medium">Drop Excel file here</p>
            <p className="text-gray-500 text-sm">.xlsx or .xls files</p>
          </div>
        </div>
      )}

      <div
        className="bg-[#f0f2f5] px-4 py-3 flex items-end gap-2 relative"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Multiline hint tooltip */}
        {showMultilineHint && (
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-gray-800 text-white text-xs px-3 py-1.5 rounded-lg shadow-lg">
            Shift+Enter for new line
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
          </div>
        )}

        {/* Attachment button */}
        <button
          onClick={handleAttachClick}
          disabled={disabled}
          className={`w-10 h-10 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors ${disabled ? 'opacity-50' : ''}`}
          title="Attach Excel file (.xlsx, .xls)"
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

        <div className={`flex-1 bg-white rounded-3xl flex items-end relative ${shake ? 'animate-shake' : ''}`}>
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS + 100))}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 px-4 py-3 text-sm resize-none outline-none rounded-3xl max-h-32"
            style={{ minHeight: '44px' }}
          />
          {/* Character counter */}
          {showCharCounter && (
            <div className={`absolute right-3 bottom-1 text-xs ${isOverLimit ? 'text-red-500' : isNearLimit ? 'text-amber-500' : 'text-gray-400'}`}>
              {charCount}/{MAX_CHARS}
            </div>
          )}
        </div>

        <button
          onClick={message.trim() ? handleSend : handleMicClick}
          disabled={disabled || isOverLimit}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            message.trim() && !disabled && !isOverLimit
              ? 'bg-[#25D366] text-white hover:bg-[#128C7E]'
              : 'bg-[#25D366] text-white hover:bg-[#128C7E]'
          } ${disabled || isOverLimit ? 'opacity-50' : ''}`}
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
