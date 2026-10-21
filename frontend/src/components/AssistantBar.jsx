import React, { useState } from 'react';
import { Sparkles, Send, Bot, X } from 'lucide-react';

export default function AssistantBar({ onChatSubmit, isTyping = false, activeReply, onCloseReply }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!query.trim() || isTyping) return;
    onChatSubmit(query.trim());
    setQuery('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <form className="assistant-bar-card" onSubmit={handleSubmit}>
        <Sparkles size={18} color="#8C9A90" />
        <input
          type="text"
          className="assistant-bar-input"
          placeholder="Ask Aheadly..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isTyping}
        />
        <button
          type="submit"
          className="assistant-bar-btn"
          disabled={!query.trim() || isTyping}
          title="Send query to Alexa+ assistant"
        >
          <Send size={15} />
        </button>
      </form>

      {/* Inline Assistant Response Display (if active) */}
      {activeReply && (
        <div
          style={{
            background: '#FFFDF9',
            border: '1px solid #EBDCC8',
            borderRadius: '14px',
            padding: '14px 18px',
            boxShadow: '0 2px 8px rgba(0, 0, 53, 0.05)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            position: 'relative'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#000035', fontWeight: '700', fontSize: '13px' }}>
              <Bot size={16} color="#000035" />
              <span>Aheadly Assistant</span>
            </div>
            <button
              onClick={onCloseReply}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#8C9A90' }}
            >
              <X size={15} />
            </button>
          </div>

          <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#2B2C38', whiteSpace: 'pre-wrap' }}>
            {activeReply.reply || activeReply.text}
          </div>

          {activeReply.tools_invoked && activeReply.tools_invoked.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
              <span style={{ fontSize: '11px', color: '#8C9A90' }}>MCP Dispatched:</span>
              {activeReply.tools_invoked.map((t, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: '10.5px',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: '#E5F2FD',
                    color: '#1A6CA7',
                    fontWeight: '600',
                    fontFamily: 'var(--font-mono)'
                  }}
                >
                  ⚡ {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
