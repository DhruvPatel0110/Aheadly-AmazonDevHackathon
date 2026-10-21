import React, { useState, useEffect } from 'react';
import {
  Terminal,
  Activity,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Layers
} from 'lucide-react';

export default function McpToolCallLog({ logs = [], onRefresh, onClear }) {
  const [expandedId, setExpandedId] = useState(null);
  const [filterTool, setFilterTool] = useState('all');
  const [registeredTools, setRegisteredTools] = useState([]);
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' | 'schemas'

  useEffect(() => {
    fetch('/api/mcp/tools')
      .then((res) => res.json())
      .then((data) => setRegisteredTools(data))
      .catch((err) => console.error('Failed to load MCP tools schema:', err));
  }, []);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const filteredLogs = logs.filter((log) => {
    const tName = log.tool_name || log.tool;
    if (filterTool === 'all') return true;
    return tName === filterTool;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header & Sub-Tabs */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #EBDCC8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#FFF9F0',
          flexShrink: 0
        }}
      >
        <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 53, 0.04)', padding: '3px', borderRadius: 'var(--radius-full)' }}>
          <button
            className={`filter-pill ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
            style={{ fontSize: '11.5px', padding: '4px 10px' }}
          >
            <Activity size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
            Calls ({logs.length})
          </button>
          <button
            className={`filter-pill ${activeTab === 'schemas' ? 'active' : ''}`}
            onClick={() => setActiveTab('schemas')}
            style={{ fontSize: '11.5px', padding: '4px 10px' }}
          >
            <Layers size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
            Tools ({registeredTools.length || 8})
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={onRefresh}
            title="Refresh tool call log"
          >
            <RefreshCw size={12} />
          </button>
          {activeTab === 'logs' && (
            <button
              className="btn btn-outline btn-sm"
              onClick={onClear}
              title="Clear tool call history"
              style={{ color: '#C52222' }}
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {activeTab === 'schemas' ? (
          /* Registered MCP Tools Schema Catalog */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '2px' }}>
              8 Registered MCP Tools (Spec 2025-11-25+ over Streamable HTTP):
            </div>
            {registeredTools.map((t) => (
              <div key={t.name} style={{ background: '#FFFDF9', border: '1px solid #EBDCC8', borderRadius: '12px', padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12.5px', fontWeight: '700', color: '#000035' }}>
                    {t.name}
                  </span>
                  <span className="status-pill blue" style={{ fontSize: '10px', padding: '2px 7px' }}>
                    JSON-RPC 2.0
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: '#6B7280', margin: '4px 0 8px 0' }}>
                  {t.description}
                </p>
                {t.inputSchema && (
                  <div style={{ background: '#FFF8EE', border: '1px solid #EBDCC8', borderRadius: '8px', padding: '10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#000035', maxHeight: '120px', overflowY: 'auto' }}>
                    {JSON.stringify(t.inputSchema, null, 2)}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          /* Real-time Tool Call Invocations */
          <>
            {filteredLogs.length === 0 ? (
              <div
                style={{
                  background: '#FFFDF9',
                  border: '1px solid #EBDCC8',
                  borderRadius: '12px',
                  padding: '30px 16px',
                  textAlign: 'center',
                  color: '#8C9A90',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <Terminal size={28} opacity={0.4} />
                <span style={{ fontSize: '13px', fontWeight: '600', color: '#000035' }}>No MCP tool calls recorded yet.</span>
                <span style={{ fontSize: '11.5px', color: '#8C9A90' }}>
                  Trigger an action (upload source, verify date, ask assistant) to inspect real JSON-RPC dispatches.
                </span>
              </div>
            ) : (
              filteredLogs.map((log) => {
                const isExpanded = expandedId === log.id;
                const isSuccess = log.status === 'success' || !log.error;
                const latency = log.latency_ms !== undefined ? `${Math.round(log.latency_ms)}ms` : '<1ms';
                const toolName = log.tool_name || log.tool;
                const toolArgs = log.arguments || log.parameters || {};
                const toolResult = log.result || log.response || log.error || {};

                return (
                  <div
                    key={log.id}
                    style={{
                      background: '#FFFDF9',
                      border: '1px solid #EBDCC8',
                      borderLeft: isSuccess ? '3.5px solid #10B981' : '3.5px solid #EF4444',
                      borderRadius: '10px',
                      padding: '10px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-sm)'
                    }}
                    onClick={() => toggleExpand(log.id)}
                  >
                    {/* Tool Call Row */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                        {isExpanded ? <ChevronDown size={14} color="#8C9A90" /> : <ChevronRight size={14} color="#8C9A90" />}
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: '700', color: '#000035' }}>
                          {toolName}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span
                          className={`status-pill ${isSuccess ? 'green' : 'amber'}`}
                          style={{ fontSize: '10px', padding: '1px 6px' }}
                        >
                          <span className="status-dot" />
                          <span>{isSuccess ? '200 OK' : 'ERROR'}</span>
                        </span>
                        <span style={{ fontSize: '11px', color: '#8C9A90', fontFamily: 'var(--font-mono)' }}>
                          {latency}
                        </span>
                      </div>
                    </div>

                    {/* Timestamp & Params Summary */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: '#8C9A90' }}>
                      <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'now'}</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>
                        params: {Object.keys(toolArgs).length}
                      </span>
                    </div>

                    {/* Expanded JSON Payloads */}
                    {isExpanded && (
                      <div
                        style={{
                          borderTop: '1px solid #EBDCC8',
                          paddingTop: '8px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          cursor: 'default'
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div>
                          <div style={{ fontSize: '10.5px', fontWeight: '700', color: '#000035', marginBottom: '2px' }}>
                            INPUT PARAMETERS (JSON-RPC)
                          </div>
                          <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '6px', padding: '8px', fontFamily: 'var(--font-mono)', fontSize: '11px', maxHeight: '110px', overflowY: 'auto' }}>
                            {JSON.stringify(toolArgs, null, 2)}
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '10.5px', fontWeight: '700', color: '#197843', marginBottom: '2px' }}>
                            OUTPUT RESPONSE PAYLOAD
                          </div>
                          <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '6px', padding: '8px', fontFamily: 'var(--font-mono)', fontSize: '11px', maxHeight: '150px', overflowY: 'auto' }}>
                            {JSON.stringify(toolResult, null, 2)}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </>
        )}
      </div>
    </div>
  );
}
