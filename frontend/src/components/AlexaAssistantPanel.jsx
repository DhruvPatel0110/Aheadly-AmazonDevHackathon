import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Terminal } from 'lucide-react';

const SUGGESTIONS = [
  "Show evidence for Netflix",
  "How do I cancel Netflix?",
  "Confirm date as 2026-10-20",
  "Remind me 3 days before",
  "What bills are due soon?",
  "I paid my Airtel Wi-Fi bill"
];

export default function AlexaAssistantPanel({ activeDeadlineId, onDeadlineAction }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'alexa',
      text: "Hello Dhruv! I'm Aheadly, your **Deadline Rescue Agent**. I verify deadlines directly against your bills and emails, ground every date in verbatim evidence, and prepare step-by-step follow-through guides.",
      tools_invoked: ['mcp_initialized'],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (messageText) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || isTyping) return;

    const userMsg = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          active_deadline_id: activeDeadlineId || null
        })
      });

      let data = null;
      const text = await res.text();
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(text || `Server error (${res.status})`);
      }
      if (!res.ok) {
        throw new Error(data?.detail || 'Failed to chat with Alexa+ agent.');
      }

      const botMsg = {
        id: `bot_${Date.now()}`,
        sender: 'alexa',
        text: data.reply || data.response || "I've processed your request via MCP.",
        tools_invoked: data.tools_invoked || data.tools_called || (data.tool_invoked ? [data.tool_invoked] : []),
        tool_results: data.data || data.tool_results || null,
        evidence: data.evidence || data.data?.evidence_snippet || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, botMsg]);

      if (onDeadlineAction) {
        onDeadlineAction(data);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: 'alexa',
          text: `⚠️ **Error communicating with MCP agent:** ${err.message}`,
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const renderFormattedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={index} style={{ color: '#000035', fontWeight: '700' }}>
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#FFFDF9' }}>
      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}
      >
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
                gap: '4px'
              }}
            >
              {/* Sender label & Timestamp */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#8C9A90' }}>
                {!isUser && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#000035', fontWeight: '600' }}>
                    <Bot size={13} />
                    Aheadly
                  </span>
                )}
                {isUser && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600', color: '#000035' }}>
                    <User size={13} />
                    You
                  </span>
                )}
                <span>• {msg.timestamp}</span>
              </div>

              {/* Message Bubble */}
              <div
                style={{
                  maxWidth: '88%',
                  padding: '12px 16px',
                  borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: isUser ? '#000035' : '#FFF9F0',
                  border: isUser ? '1px solid #000035' : '1px solid #EBDCC8',
                  color: isUser ? '#FFF0DB' : '#2B2C38',
                  fontSize: '13px',
                  lineHeight: '1.6',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {renderFormattedText(msg.text)}
                </div>

                {/* Evidence Drawer in chat message */}
                {msg.evidence && (
                  <div
                    style={{
                      marginTop: '8px',
                      background: '#FAF2E5',
                      borderLeft: '3px solid #000035',
                      padding: '8px 12px',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '12px',
                      color: '#374151',
                      fontStyle: 'italic'
                    }}
                  >
                    “{msg.evidence}”
                  </div>
                )}

                {/* Invoked MCP Tool Badges */}
                {msg.tools_invoked && msg.tools_invoked.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(0, 0, 53, 0.08)' }}>
                    <span style={{ fontSize: '10px', color: '#8C9A90', fontFamily: 'var(--font-mono)' }}>
                      MCP Tool:
                    </span>
                    {msg.tools_invoked.map((t, idx) => (
                      <span
                        key={idx}
                        className="status-pill blue"
                        style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        ⚡ {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isTyping && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#000035', fontSize: '12px', padding: '4px 8px' }}>
            <span className="status-dot" style={{ backgroundColor: '#000035' }} />
            <span>Calling MCP tools...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts */}
      <div
        style={{
          padding: '8px 14px',
          borderTop: '1px solid #EBDCC8',
          background: '#FFF8EE',
          display: 'flex',
          gap: '6px',
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}
      >
        {SUGGESTIONS.map((item, idx) => (
          <button
            key={idx}
            className="filter-pill"
            onClick={() => handleSend(item)}
            style={{
              fontSize: '11px',
              padding: '4px 10px',
              background: '#FFFDF9',
              border: '1px solid #EBDCC8',
              flexShrink: 0
            }}
          >
            <Sparkles size={11} color="#8C9A90" style={{ display: 'inline', marginRight: '4px' }} />
            {item}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <div
        style={{
          padding: '12px 14px',
          borderTop: '1px solid #EBDCC8',
          background: '#FFFDF9',
          display: 'flex',
          gap: '8px',
          alignItems: 'center'
        }}
      >
        <input
          type="text"
          className="input-cream"
          placeholder="Ask Aheadly (e.g., 'How do I cancel?', 'Confirm date')..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSend();
          }}
          style={{ flex: 1 }}
        />
        <button
          className="btn btn-navy"
          onClick={() => handleSend()}
          disabled={!input.trim() || isTyping}
          style={{ padding: '8px 14px' }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
