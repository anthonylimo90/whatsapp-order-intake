export function TypingIndicator() {
  return (
    <div className="flex justify-start mb-2">
      <div className="message-bubble incoming">
        <div className="typing-indicator flex items-center py-1">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}
