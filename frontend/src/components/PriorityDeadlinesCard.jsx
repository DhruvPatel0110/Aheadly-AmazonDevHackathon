import React, { useState } from 'react';
import {
  List,
  Calendar,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Shield,
  Zap,
  Radio,
  Tv,
  CheckCircle2,
  XCircle,
  Bell,
  FileSearch,
  Download,
  RotateCcw,
  AlertCircle
} from 'lucide-react';

// Brand icon / avatar renderer
function ProviderAvatar({ name = '', category = '' }) {
  const lower = name.toLowerCase();

  if (lower.includes('netflix')) {
    return (
      <div className="provider-logo-box" style={{ background: '#000000' }}>
        <span style={{ color: '#E50914', fontWeight: '900', fontSize: '19px', fontFamily: 'Impact, sans-serif' }}>
          N
        </span>
      </div>
    );
  }
  if (lower.includes('hdfc')) {
    return (
      <div className="provider-logo-box" style={{ background: '#D61B23', padding: '2px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: '1' }}>
          <span style={{ color: '#FFFFFF', fontSize: '9px', fontWeight: '900', letterSpacing: '-0.03em' }}>HDFC</span>
          <span style={{ color: '#FFFFFF', fontSize: '8px', fontWeight: '700' }}>ERGO</span>
        </div>
      </div>
    );
  }
  if (lower.includes('airtel')) {
    return (
      <div className="provider-logo-box" style={{ background: '#E60000' }}>
        <span style={{ color: '#FFFFFF', fontWeight: '900', fontSize: '11px', letterSpacing: '-0.02em' }}>
          airtel
        </span>
      </div>
    );
  }
  if (lower.includes('spotify')) {
    return (
      <div className="provider-logo-box" style={{ background: '#1DB954' }}>
        <Radio size={20} color="#FFFFFF" />
      </div>
    );
  }
  if (lower.includes('cred')) {
    return (
      <div className="provider-logo-box" style={{ background: '#121212' }}>
        <Shield size={18} color="#FFFFFF" />
      </div>
    );
  }
  if (lower.includes('tata')) {
    return (
      <div className="provider-logo-box" style={{ background: '#0F52BA' }}>
        <Zap size={18} color="#FFFFFF" />
      </div>
    );
  }

  // Fallback category colors
  const initials = name ? name.slice(0, 2).toUpperCase() : 'DL';
  const bg = category === 'insurance' ? '#D61B23' : category === 'utility' ? '#0F52BA' : '#2A2C38';
  return (
    <div className="provider-logo-box" style={{ background: bg }}>
      <span style={{ fontSize: '13px', fontWeight: '700' }}>{initials}</span>
    </div>
  );
}

// Compute days remaining and sublabel text
function getUrgencyInfo(dateStr, obligationType, category, status) {
  if (status === 'completed') {
    return { text: '✓ Payment completed', isUrgent: false, isCompleted: true };
  }
  if (status === 'cancelled') {
    return { text: 'Cancelled', isUrgent: false, isCancelled: true };
  }
  if (!dateStr || dateStr === 'UNVERIFIED') {
    return { text: 'Date unverified', isUrgent: true };
  }
  try {
    const target = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    target.setHours(0, 0, 0, 0);
    const diff = Math.round((target - today) / (1000 * 60 * 60 * 24));

    if (diff === 0) return { text: 'Due today', isUrgent: true };
    if (diff === 1) return { text: 'Due tomorrow', isUrgent: true };
    if (diff > 1 && diff <= 5) {
      if (obligationType === 'trial_ending') return { text: `Trial ends in ${diff} days`, isUrgent: true };
      if (obligationType === 'payment_due') return { text: `Bill payment in ${diff} days`, isUrgent: true };
      return { text: `Due in ${diff} days`, isUrgent: true };
    }
    if (diff < 0) return { text: `Overdue by ${Math.abs(diff)}d`, isUrgent: true };

    // Neutral subtext
    if (category === 'insurance') return { text: 'Annual premium', isUrgent: false };
    if (obligationType === 'trial_ending') return { text: 'Trial cancellation', isUrgent: false };
    if (obligationType === 'renewal') return { text: 'Monthly renewal', isUrgent: false };
    return { text: 'Upcoming payment', isUrgent: false };
  } catch {
    return { text: 'Scheduled', isUrgent: false };
  }
}

// Format date into "20 Oct 2026"
function formatDateDisplay(dateStr) {
  if (!dateStr || dateStr === 'UNVERIFIED') return 'Unverified';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function PriorityDeadlinesCard({
  deadlines = [],
  selectedId,
  onSelectDeadline,
  onMarkCompleted,
  onRemindLater,
  onCancelSubscription,
  onReopen,
  onInspectEvidence
}) {
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'needs_review' | 'upcoming' | 'completed' | 'cancelled'
  const [expandedId, setExpandedId] = useState(null);

  // Filter deadlines
  const filtered = deadlines.filter((item) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'needs_review') return item.status === 'needs_review' || item.status === 'date_unverified';
    if (activeFilter === 'upcoming') return item.status === 'upcoming' || item.status === 'confirmed';
    if (activeFilter === 'completed') return item.status === 'completed';
    if (activeFilter === 'cancelled') return item.status === 'cancelled';
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (a.candidate_date === 'UNVERIFIED' && b.candidate_date !== 'UNVERIFIED') return 1;
    if (a.candidate_date !== 'UNVERIFIED' && b.candidate_date === 'UNVERIFIED') return -1;
    if (a.candidate_date && b.candidate_date) {
      return new Date(a.candidate_date) - new Date(b.candidate_date);
    }
    return 0;
  });

  const allCount = deadlines.length;
  const reviewCount = deadlines.filter((d) => d.status === 'needs_review' || d.status === 'date_unverified').length;
  const upcomingCount = deadlines.filter((d) => d.status === 'upcoming' || d.status === 'confirmed').length;
  const completedCount = deadlines.filter((d) => d.status === 'completed').length;
  const cancelledCount = deadlines.filter((d) => d.status === 'cancelled').length;

  const handleRowClick = (item) => {
    onSelectDeadline(item);
    setExpandedId((prev) => (prev === item.id ? null : item.id));
  };

  return (
    <div className="card">
      {/* Header with Title and Filter Pills */}
      <div className="card-header-tabs">
        <div className="card-title">
          <List size={19} color="#000035" />
          <span>Priority deadlines</span>
        </div>

        <div className="filter-pills">
          <button
            className={`filter-pill ${activeFilter === 'all' ? 'active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            All ({allCount})
          </button>
          <button
            className={`filter-pill ${activeFilter === 'needs_review' ? 'active' : ''}`}
            onClick={() => setActiveFilter('needs_review')}
          >
            Needs review ({reviewCount})
          </button>
          <button
            className={`filter-pill ${activeFilter === 'upcoming' ? 'active' : ''}`}
            onClick={() => setActiveFilter('upcoming')}
          >
            Upcoming ({upcomingCount})
          </button>
          <button
            className={`filter-pill ${activeFilter === 'completed' ? 'active' : ''}`}
            onClick={() => setActiveFilter('completed')}
          >
            Completed ({completedCount})
          </button>
          {cancelledCount > 0 && (
            <button
              className={`filter-pill ${activeFilter === 'cancelled' ? 'active' : ''}`}
              onClick={() => setActiveFilter('cancelled')}
            >
              Cancelled ({cancelledCount})
            </button>
          )}
        </div>
      </div>

      {/* Deadlines Rows List */}
      <div className="deadline-rows">
        {filtered.length === 0 ? (
          <div style={{ padding: '36px 20px', textAlign: 'center', color: '#8C9A90', fontSize: '13px' }}>
            No deadlines in this category. Click "Ingest Source" to add bills, trials, and notices.
          </div>
        ) : (
          sorted.map((item) => {
            const urgency = getUrgencyInfo(item.candidate_date, item.obligation_type, item.category, item.status);
            const isSelected = selectedId === item.id;
            const isExpanded = expandedId === item.id || (isSelected && expandedId === null);
            const isVerified = item.verification_status === 'user_confirmed' || item.status === 'confirmed';
            const isReview = item.status === 'needs_review' || item.status === 'date_unverified';

            return (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  borderBottom: '1px solid #F0E6D8'
                }}
              >
                {/* Main Row */}
                <div
                  className={`deadline-row ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleRowClick(item)}
                  style={{ borderBottom: 'none' }}
                >
                  {/* 1. Avatar */}
                  <ProviderAvatar name={item.provider_name} category={item.category} />

                  {/* 2. Provider Info */}
                  <div className="provider-info">
                    <span className="provider-name">{item.provider_name}</span>
                    <span className="provider-category">{item.category}</span>
                  </div>

                  {/* 3. Date & Urgency */}
                  <div className="deadline-date-col">
                    <div className="deadline-date-text">
                      <Calendar size={13} color="#8C9A90" />
                      <span>{formatDateDisplay(item.candidate_date)}</span>
                    </div>
                    <span
                      className={`deadline-urgency-sub ${
                        urgency.isCompleted ? 'neutral' : urgency.isUrgent ? '' : 'neutral'
                      }`}
                      style={{ color: urgency.isCompleted ? '#10B981' : undefined }}
                    >
                      {urgency.text}
                    </span>
                  </div>

                  {/* 4. Amount */}
                  <div className="deadline-amount">
                    {item.amount !== null && item.amount !== undefined ? (
                      <span>
                        ₹{Number(item.amount).toLocaleString('en-IN')}
                        {item.recurrence === 'monthly' ? '/mo' : ''}
                      </span>
                    ) : (
                      <span style={{ color: '#8C9A90', fontSize: '12px' }}>—</span>
                    )}
                  </div>

                  {/* 5. Status Pill */}
                  <div>
                    {item.status === 'completed' ? (
                      <span className="status-pill green">
                        <span className="status-dot" />
                        <span>Completed</span>
                      </span>
                    ) : item.status === 'cancelled' ? (
                      <span className="status-pill gray">
                        <span className="status-dot" />
                        <span>Cancelled</span>
                      </span>
                    ) : isReview ? (
                      <span className="status-pill amber">
                        <span className="status-dot" />
                        <span>Needs review</span>
                      </span>
                    ) : isVerified ? (
                      <span className="status-pill green">
                        <span className="status-dot" />
                        <span>Evidence verified</span>
                      </span>
                    ) : (
                      <span className="status-pill blue">
                        <span className="status-dot" />
                        <span>Upcoming</span>
                      </span>
                    )}
                  </div>

                  {/* 6. Chevron Expand Icon */}
                  <div style={{ color: '#8C9A90', display: 'flex', justifyContent: 'flex-end' }}>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronRight size={16} />}
                  </div>
                </div>

                {/* Expanded Action Drawer with 3 Required Actions */}
                {isExpanded && (
                  <div
                    style={{
                      background: '#FFFDF9',
                      borderTop: '1px solid #EBDCC8',
                      padding: '12px 18px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '10px'
                    }}
                  >
                    {/* Left: Secondary actions (Inspect Evidence & .ics) */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        className="btn btn-outline btn-sm"
                        style={{ fontSize: '11.5px', padding: '4px 10px', gap: '5px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onInspectEvidence && onInspectEvidence(item);
                        }}
                      >
                        <FileSearch size={13} />
                        <span>Inspect Evidence</span>
                      </button>

                      <a
                        href={`/api/deadlines/${item.id}/ics`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-outline btn-sm"
                        style={{ fontSize: '11.5px', padding: '4px 10px', gap: '5px' }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Download size={13} />
                        <span>.ics Calendar</span>
                      </a>
                    </div>

                    {/* Right: The 3 Core Required Actions (Completed, Remind Later, Cancel Subscription) */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* ACTION 1: COMPLETED / MARK PAID */}
                      {item.status !== 'completed' ? (
                        <button
                          className="btn btn-sm"
                          style={{
                            background: '#000035',
                            color: '#FFF0DB',
                            fontSize: '11.5px',
                            padding: '5px 13px',
                            gap: '5px',
                            fontWeight: '600'
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onMarkCompleted && onMarkCompleted(item.id);
                          }}
                          title="Mark this obligation / payment as completed"
                        >
                          <CheckCircle2 size={13} color="#10B981" />
                          <span>
                            {item.category === 'utility' || item.category === 'broadband' || item.obligation_type === 'payment_due'
                              ? 'Mark Paid'
                              : 'Completed'}
                          </span>
                        </button>
                      ) : (
                        <button
                          className="btn btn-outline btn-sm"
                          style={{ fontSize: '11.5px', padding: '4px 10px', gap: '5px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onReopen && onReopen(item.id);
                          }}
                          title="Reopen completed obligation"
                        >
                          <RotateCcw size={12} />
                          <span>Reopen</span>
                        </button>
                      )}

                      {/* ACTION 2: REMIND LATER */}
                      <button
                        className="btn btn-outline btn-sm"
                        style={{
                          borderColor: '#D97706',
                          color: '#B45309',
                          background: '#FFFDF9',
                          fontSize: '11.5px',
                          padding: '4px 12px',
                          gap: '5px',
                          fontWeight: '600'
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemindLater && onRemindLater(item);
                        }}
                        title="Configure an advance alert reminder for later"
                      >
                        <Bell size={13} />
                        <span>Remind Later</span>
                      </button>

                      {/* ACTION 3: CANCEL / DISMISS */}
                      {item.status !== 'cancelled' && item.status !== 'dismissed' ? (
                        <button
                          className="btn btn-outline btn-sm"
                          style={{
                            borderColor: '#DC2626',
                            color: '#DC2626',
                            background: '#FFFDF9',
                            fontSize: '11.5px',
                            padding: '4px 12px',
                            gap: '5px',
                            fontWeight: '600'
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onCancelSubscription && onCancelSubscription(item.id);
                          }}
                          title={item.category === 'subscription' ? 'Cancel subscription before renewal' : 'Dismiss or cancel obligation'}
                        >
                          <XCircle size={13} />
                          <span>
                            {item.category === 'subscription' || item.obligation_type === 'trial_ending'
                              ? 'Cancel Subscription'
                              : 'Dismiss / Cancel'}
                          </span>
                        </button>
                      ) : (
                        <span style={{ fontSize: '11.5px', color: '#6B7280', fontStyle: 'italic' }}>
                          {item.category === 'subscription' ? 'Cancelled' : 'Resolved'}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
