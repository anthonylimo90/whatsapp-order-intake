import { useEffect, useRef, useMemo } from 'react';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { DateSeparator } from './DateSeparator';
import { useChatStore } from '../../store/chatStore';
import { RefreshCw, Paperclip, Mic } from 'lucide-react';
import type { Message } from '../../types';

// Helper to check if two dates are the same day
function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

// Helper to check if messages should be grouped (same sender within 2 min)
function shouldGroup(msg1: Message, msg2: Message): boolean {
  if (msg1.role !== msg2.role) return false;
  const time1 = new Date(msg1.created_at).getTime();
  const time2 = new Date(msg2.created_at).getTime();
  const TWO_MINUTES = 2 * 60 * 1000;
  return Math.abs(time2 - time1) < TWO_MINUTES;
}

interface ProcessedMessage {
  type: 'message' | 'date-separator';
  message?: Message;
  date?: Date;
  isFirstInGroup?: boolean;
  isLastInGroup?: boolean;
}

export function ChatContainer() {
  const {
    messages,
    isProcessing,
    sendMessage,
    uploadExcelFile,
    resetChat,
    currentExtraction,
    cumulativeState,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  const needsClarification = currentExtraction?.requires_clarification ||
    (cumulativeState?.requires_clarification && cumulativeState?.pending_clarifications?.length > 0);

  // Process messages to add date separators and grouping info
  const processedMessages = useMemo((): ProcessedMessage[] => {
    if (messages.length === 0) return [];

    const result: ProcessedMessage[] = [];
    let lastDate: Date | null = null;

    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      const msgDate = new Date(msg.created_at);

      // Add date separator if day changed
      if (!lastDate || !isSameDay(lastDate, msgDate)) {
        result.push({ type: 'date-separator', date: msgDate });
        lastDate = msgDate;
      }

      // Determine grouping
      const prevMsg = i > 0 ? messages[i - 1] : null;
      const nextMsg = i < messages.length - 1 ? messages[i + 1] : null;

      const isFirstInGroup = !prevMsg ||
        !isSameDay(new Date(prevMsg.created_at), msgDate) ||
        !shouldGroup(prevMsg, msg);

      const isLastInGroup = !nextMsg ||
        !isSameDay(msgDate, new Date(nextMsg.created_at)) ||
        !shouldGroup(msg, nextMsg);

      result.push({
        type: 'message',
        message: msg,
        isFirstInGroup,
        isLastInGroup,
      });
    }

    return result;
  }, [messages]);

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

        {processedMessages.map((item, index) => {
          if (item.type === 'date-separator' && item.date) {
            return <DateSeparator key={`date-${index}`} date={item.date} />;
          }
          if (item.type === 'message' && item.message) {
            return (
              <MessageBubble
                key={item.message.id}
                message={item.message}
                isFirstInGroup={item.isFirstInGroup}
                isLastInGroup={item.isLastInGroup}
              />
            );
          }
          return null;
        })}

        {isProcessing && <TypingIndicator />}

        {needsClarification && !isProcessing && (
          <div className="text-center py-3">
            <div className="inline-flex items-center gap-2 bg-amber-100 text-amber-800 text-sm px-4 py-2 rounded-full shadow-sm animate-pulse">
              <span className="text-lg">⚠️</span>
              <span>
                {cumulativeState?.pending_clarifications?.length || 1} item(s) need clarification
              </span>
            </div>
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
