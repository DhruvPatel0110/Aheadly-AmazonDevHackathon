import React from 'react';
import { FileText, AlertCircle, Calendar, CheckCircle2 } from 'lucide-react';

export default function SummaryCards({ stats, loading = false }) {
  const isLoaded = stats && !loading;

  const cards = [
    {
      id: 'tracked',
      label: 'Tracked obligations',
      value: isLoaded ? (stats.total_tracked ?? 0) : '—',
      sublabel: 'Active deadlines',
      sublabelColor: '#10B981',
      icon: FileText,
      iconBg: '#E7F0FA',
      iconColor: '#2B6CB0'
    },
    {
      id: 'needs_review',
      label: 'Needs review',
      value: isLoaded ? (stats.needs_review ?? 0) : '—',
      sublabel: 'Requires your action',
      sublabelColor: '#8C9A90',
      icon: AlertCircle,
      iconBg: '#FDF2DE',
      iconColor: '#D97706'
    },
    {
      id: 'upcoming',
      label: 'Upcoming this week',
      value: isLoaded ? (stats.upcoming ?? 0) : '—',
      sublabel: 'Next 7 days',
      sublabelColor: '#8C9A90',
      icon: Calendar,
      iconBg: '#EAF1F8',
      iconColor: '#1A6CA7'
    },
    {
      id: 'completed',
      label: 'Completed',
      value: isLoaded ? (stats.completed ?? 0) : '—',
      sublabel: 'Resolved',
      sublabelColor: '#8C9A90',
      icon: CheckCircle2,
      iconBg: '#E7F7ED',
      iconColor: '#10B981'
    }
  ];

  return (
    <div className="stats-grid">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.id} className="stat-card">
            <div className="stat-icon-circle" style={{ backgroundColor: card.iconBg }}>
              <Icon size={20} color={card.iconColor} />
            </div>
            <div className="stat-info">
              <span className="stat-label">{card.label}</span>
              <div className="stat-value-row">
                <span className="stat-number">{card.value}</span>
                <span className="stat-sublabel" style={{ color: card.sublabelColor }}>
                  {card.sublabel}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
