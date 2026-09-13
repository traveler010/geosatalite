import { useEffect, useRef } from 'react';

export default function ChatMessage({ type, text, result }) {
  const ref = useRef(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, []);

  const isUser = type === 'user';

  return (
    <div
      ref={ref}
      className={`flex gap-2 max-w-[95%] animate-slide-in ${
        isUser ? 'self-end flex-row-reverse' : ''
      }`}
    >
      {/* Avatar */}
      <div
        className={`grid place-items-center shrink-0 w-[27px] h-[27px] rounded-lg text-[10px] font-bold border ${
          isUser
            ? 'border-gold/35 bg-gold/10 text-gold'
            : 'border-blue-bright/35 bg-blue/15 text-blue-bright'
        }`}
      >
        {isUser ? 'YOU' : 'AI'}
      </div>

      {/* Bubble */}
      <div
        className={`px-[11px] py-[9px] border text-xs leading-relaxed ${
          isUser
            ? 'border-gold/20 rounded-[10px_4px_10px_10px] bg-chat-user-bg text-gold-light'
            : 'border-border rounded-[4px_10px_10px_10px] bg-chat-ai-bg text-[#cdd9e8]'
        }`}
      >
        {text}
        {result && (
          <span className="block mt-[7px] pt-[7px] border-t border-border text-emerald font-mono text-[10px]">
            {result}
          </span>
        )}
      </div>
    </div>
  );
}
