import React from 'react';
import { Search, Calendar, Bell } from 'lucide-react';

export default function Header({ searchQuery, onSearchChange, notificationCount = 1 }) {
  // Format current date nicely like "Sat, 17 Oct 2026"
  const formattedDate = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });

  return (
    <header className="top-header">
      {/* Search Input Bar */}
      <div className="header-search">
        <Search size={16} color="#8C9A90" />
        <input
          type="text"
          className="header-search-input"
          placeholder="Search deadlines, sources, or ask anything..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Header Actions */}
      <div className="header-actions">
        <div className="header-date">
          <Calendar size={15} color="#8C9A90" />
          <span>{formattedDate}</span>
        </div>

        <button className="header-icon-btn" title="Notifications">
          <Bell size={18} />
          {notificationCount > 0 && <span className="header-icon-dot" />}
        </button>

        <div className="header-avatar" title="Dhruv Patel (Alexa+ Track)">
          DP
        </div>
      </div>
    </header>
  );
}
