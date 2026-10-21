import React from 'react';
import {
  ShieldCheck,
  LayoutDashboard,
  FileText,
  Calendar,
  Bell,
  Activity,
  Settings,
  Plus
} from 'lucide-react';

export default function Sidebar({ activeTab, onSelectTab, onOpenIngest, isMcpOnline = true }) {
  const navItems = [
    { key: 'deadlines', label: 'Deadlines', icon: Calendar },
    { key: 'sources', label: 'Sources', icon: FileText },
    { key: 'reminders', label: 'Reminders', icon: Bell },
    { key: 'mcp', label: 'MCP Activity', icon: Activity },
    { key: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="sidebar">
      <div>
        {/* Brand Header */}
        <a href="#deadlines" className="sidebar-brand" onClick={(e) => { e.preventDefault(); onSelectTab('deadlines'); }}>
          <div className="sidebar-logo-icon">
            <ShieldCheck size={22} color="#FFF0DB" />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">Deadline</span>
            <span className="sidebar-brand-sub">Rescue</span>
          </div>
        </a>

        {/* Navigation Items */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.key;
            return (
              <button
                key={item.key}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(item.key)}
              >
                <Icon size={17} color={isActive ? '#FFFFFF' : '#D3CEBF'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Controls */}
      <div className="sidebar-footer">
        <button className="btn-ingest-sidebar" onClick={onOpenIngest}>
          <Plus size={16} />
          <span>Ingest Source</span>
        </button>

        <div className="mcp-status-box">
          <div className="mcp-status-dot" style={{ backgroundColor: isMcpOnline ? '#10B981' : '#EF4444' }} />
          <div>
            <div className="mcp-status-title" style={{ color: isMcpOnline ? '#10B981' : '#EF4444' }}>
              {isMcpOnline ? 'MCP Server Online' : 'MCP Disconnected'}
            </div>
            <div className="mcp-status-desc">
              Streamable HTTP<br />Spec 2025-11-25+
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
