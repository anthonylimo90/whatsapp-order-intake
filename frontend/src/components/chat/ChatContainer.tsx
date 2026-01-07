import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { useChatStore } from '../../store/chatStore';
import { RefreshCw, Paperclip, Mic } from 'lucide-react';

export function ChatContainer() {
  const {
    messages,
    isProcessing,
    sendMessage,
    uploadExcelFile,
    resetChat,
    currentExtraction,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  const needsClarification = currentExtraction?.requires_clarification;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-[#075E54] text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center">
            <span className="text-xl">🛒</span>
          </div>
          <div>
            <h2 className="font-semibold">Kijani Supplies</h2>
            <p className="text-xs text-green-200">
              {isProcessing ? 'Processing order...' : 'Online'}
            </p>
          </div>
        </div>
        <button
          onClick={resetChat}
          className="p-2 hover:bg-white/10 rounded-full transition-colors"
          title="New conversation"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-bg p-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="bg-white rounded-lg shadow-sm p-6 max-w-md mx-auto">
              <h3 className="font-semibold text-gray-800 mb-2">
                Welcome to Kijani Supplies
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Send us your order via WhatsApp and we'll process it automatically.
              </p>
              <div className="space-y-3 text-left">
                <div className="flex items-start gap-2 text-sm text-gray-500 bg-gray-50 p-3 rounded">
                  <span className="text-lg">💬</span>
                  <span className="italic">"Hi, this is Sarah from Saruni Mara. We need 50kg rice, 20kg sugar..."</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 p-3 rounded">
                  <Mic className="w-4 h-4" />
                  <span>Send a voice note with your order</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 p-3 rounded">
                  <Paperclip className="w-4 h-4" />
                  <span>Attach an Excel order file (.xlsx)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isProcessing && <TypingIndicator />}

        {needsClarification && !isProcessing && (
          <div className="text-center py-2">
            <span className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1 rounded-full">
              Please provide clarification for the items above
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <MessageInput
        onSend={(content, messageType) => sendMessage(content, messageType)}
        onFileUpload={uploadExcelFile}
        disabled={isProcessing}
        placeholder={
          needsClarification
            ? 'Type your clarification...'
            : 'Type your order message...'
        }
      />
    </div>
  );
}
