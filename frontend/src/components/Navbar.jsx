import React from 'react';
import { ShieldCheck, Sparkles, Terminal, Activity, RotateCcw } from 'lucide-react';

export default function Navbar({ stats, onResetData, isLive, mcpLogCount }) {
  return (
    <header className="top-navbar">
      {/* Brand & Track Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'var(--grad-alexa)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)'
        }}>
          <ShieldCheck size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: '800', letterSpacing: '-0.02em', margin: 0 }}>
              Aheadly
            </h1>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600' }}>
              Deadline Rescue
            </span>
            <span className="badge badge-primary" style={{ fontSize: '10px', padding: '2px 7px' }}>
              Alexa+ Track
            </span>
            <span className="badge badge-success" style={{ fontSize: '10px', padding: '2px 7px' }}>
              ₹0 Budget Local
            </span>
          </div>
          <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: 0 }}>
            Evidence-Backed Personal Deadline Agent • Self-Hosted MCP Protocol (Spec 2025-11-25)
          </p>
        </div>
      </div>

      {/* Center Ticker / Stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div className="glass-card" style={{ padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Tracked
            </span>
            <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-main)' }}>
              {stats?.total_tracked || 0}
            </span>
          </div>
          <div style={{ width: '1px', height: '18px', background: 'var(--border-subtle)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: '#fbbf24', textTransform: 'uppercase', fontWeight: '600' }}>
              Review
            </span>
            <span style={{ fontSize: '15px', fontWeight: '700', color: '#fbbf24' }}>
              {stats?.needs_review || 0}
            </span>
          </div>
          <div style={{ width: '1px', height: '18px', background: 'var(--border-subtle)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: '#34d399', textTransform: 'uppercase', fontWeight: '600' }}>
              Confirmed
            </span>
            <span style={{ fontSize: '15px', fontWeight: '700', color: '#34d399' }}>
              {(stats?.confirmed || 0) + (stats?.upcoming || 0)}
            </span>
          </div>
        </div>
      </div>

      {/* Right Controls: MCP Status & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(6, 182, 212, 0.08)',
          border: '1px solid rgba(6, 182, 212, 0.25)',
          padding: '5px 12px',
          borderRadius: 'var(--radius-full)'
        }}>
          <span className="live-dot live-dot-alexa" />
          <span style={{ fontSize: '12px', fontWeight: '600', color: '#38bdf8' }}>
            MCP Streamable HTTP
          </span>
          <span style={{ fontSize: '11px', opacity: 0.7, color: '#38bdf8' }}>
            ({mcpLogCount || 0} calls)
          </span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onResetData}
          title="Clear and reset test database"
        >
          <RotateCcw size={13} />
          Reset Demo
        </button>
      </div>
    </header>
  );
}
