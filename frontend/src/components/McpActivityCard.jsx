import React from 'react';
import { Share2, Clock, CheckCircle2, RotateCw } from 'lucide-react';

export default function McpActivityCard({ logs = [], onViewFullLog }) {
  const displayLogs = logs.slice(0, 3);

  const formatTime = (ts) => {
    if (!ts) return '—';
    try {
      return new Date(ts).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch {
      return '—';
    }
  };

  return (
    <div className="mcp-activity-card">
      {/* Header */}
      <div className="mcp-activity-header">
        <div className="mcp-activity-title">
          <Share2 size={16} color="#000035" />
          <span>MCP activity (live)</span>
        </div>
        <span className="mcp-view-all" onClick={onViewFullLog}>
          View full log →
        </span>
      </div>

      {/* Real-time Rows */}
      <div className="mcp-rows">
        {displayLogs.length === 0 ? (
          <div style={{ padding: '16px 8px', textAlign: 'center', color: '#8C9A90', fontSize: '12px' }}>
            No MCP tool executions recorded yet.
          </div>
        ) : (
          displayLogs.map((log) => {
            const tool = log.tool_name || log.tool || 'tool_call';
            const latency = log.latency_ms !== undefined ? `${Math.round(log.latency_ms)} ms` : '—';
            const isSuccess = log.status === 'success' || !log.error;

            return (
              <div key={log.id} className="mcp-row">
                <div className="mcp-tool-left">
                  <RotateCw size={12} color="#8C9A90" />
                  <span>{tool}</span>
                </div>

                <div className="mcp-tool-right">
                  <div className="mcp-tool-status" style={{ color: isSuccess ? '#10B981' : '#EF4444' }}>
                    <span
                      style={{
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        backgroundColor: isSuccess ? '#10B981' : '#EF4444'
                      }}
                    />
                    <span>{isSuccess ? '200 OK' : 'ERROR'}</span>
                  </div>
                  <span className="mcp-tool-latency">{latency}</span>
                  <span className="mcp-tool-time">{formatTime(log.timestamp)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
