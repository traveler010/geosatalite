import { useState, useEffect, useRef } from 'react';
import { Brain, ChevronDown, ChevronRight } from 'lucide-react';

export default function ChatMessage({ type, text, result, reasoning }) {
  const [showReasoning, setShowReasoning] = useState(false);
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
        {/* DeepSeek Reasoning Dropdown */}
        {reasoning && (
          <div className="mb-2 pb-2 border-b border-border/40">
            <button
              type="button"
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex items-center gap-1.5 text-[10px] text-blue-bright/90 hover:text-blue-bright transition-colors font-mono cursor-pointer"
            >
              <Brain className="w-3 h-3 text-purple-400" />
              <span>DeepSeek Reasoning ({showReasoning ? 'collapse' : 'view thinking'})</span>
              {showReasoning ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            {showReasoning && (
              <div className="mt-1.5 p-2 rounded bg-black/40 border border-blue-bright/20 text-[10px] font-mono text-[#a5b4fc] whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {reasoning}
              </div>
            )}
          </div>
        )}

        <div className="whitespace-pre-wrap">{text}</div>

        {result && (
          <span className="block mt-[7px] pt-[7px] border-t border-border text-emerald font-mono text-[10px]">
            {result}
          </span>
        )}
      </div>
    </div>
  );
}
