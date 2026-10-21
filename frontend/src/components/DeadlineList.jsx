import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileSearch,
  ListOrdered,
  Tag,
  ShieldCheck,
  RefreshCw,
  Info
} from 'lucide-react';

export default function DeadlineList({
  deadlines = [],
  onUpdateStatus,
  onViewEvidence,
  onPrepareNextStep,
  onRefresh
}) {
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'action_needed' | 'upcoming' | 'needs_review' | 'completed' | 'cancelled'
  const [expandedId, setExpandedId] = useState(null);
  const [nextStepData, setNextStepData] = useState({});
  const [loadingNextStep, setLoadingNextStep] = useState({});

  // Helper to calculate days remaining
  const getDaysDiff = (dateStr) => {
    if (!dateStr || dateStr === 'UNVERIFIED') return null;
    try {
      const target = new Date(dateStr);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      target.setHours(0, 0, 0, 0);
      const diffTime = target - today;
      return Math.round(diffTime / (1000 * 60 * 60 * 24));
    } catch {
      return null;
    }
  };

  // Filter deadlines based on selected tab
  const filteredDeadlines = deadlines.filter((item) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'upcoming') {
      return item.status === 'upcoming' || item.status === 'confirmed';
    }
    if (activeTab === 'action_needed') {
      return item.status === 'action_needed';
    }
    if (activeTab === 'needs_review') {
      return item.status === 'needs_review' || item.status === 'date_unverified';
    }
    if (activeTab === 'completed') {
      return item.status === 'completed';
    }
    if (activeTab === 'cancelled') {
      return item.status === 'cancelled';
    }
    return item.status === activeTab;
  });

  // Sort deadlines
  const sortedDeadlines = [...filteredDeadlines].sort((a, b) => {
    if (a.candidate_date === 'UNVERIFIED' && b.candidate_date !== 'UNVERIFIED') return 1;
    if (a.candidate_date !== 'UNVERIFIED' && b.candidate_date === 'UNVERIFIED') return -1;
    if (a.candidate_date && b.candidate_date) {
      return new Date(a.candidate_date) - new Date(b.candidate_date);
    }
    return 0;
  });

  const toggleExpand = async (item) => {
    if (expandedId === item.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(item.id);

    // Fetch next step instructions if not already cached
    if (!nextStepData[item.id] && onPrepareNextStep) {
      setLoadingNextStep((prev) => ({ ...prev, [item.id]: true }));
      try {
        const data = await onPrepareNextStep(item.id);
        setNextStepData((prev) => ({ ...prev, [item.id]: data }));
      } catch (err) {
        console.error('Failed to load next steps:', err);
      } finally {
        setLoadingNextStep((prev) => ({ ...prev, [item.id]: false }));
      }
    }
  };

  const handleDownloadIcs = (deadlineId, e) => {
    e.stopPropagation();
    window.open(`/api/deadlines/${deadlineId}/ics`, '_blank');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Tab Filter Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 53, 0.04)', padding: '3px', borderRadius: 'var(--radius-full)' }}>
          {[
            { key: 'all', label: 'All', count: deadlines.length },
            {
              key: 'upcoming',
              label: 'Upcoming',
              count: deadlines.filter((d) => d.status === 'upcoming' || d.status === 'confirmed').length
            },
            {
              key: 'action_needed',
              label: 'Action',
              count: deadlines.filter((d) => d.status === 'action_needed').length
            },
            {
              key: 'needs_review',
              label: 'Review',
              count: deadlines.filter((d) => d.status === 'needs_review' || d.status === 'date_unverified').length
            },
            {
              key: 'completed',
              label: 'Done',
              count: deadlines.filter((d) => d.status === 'completed').length
            }
          ].map((tab) => (
            <button
              key={tab.key}
              className={`filter-pill ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <span>{tab.label}</span>
              <span
                style={{
                  fontSize: '11px',
                  marginLeft: '4px',
                  opacity: 0.8
                }}
              >
                ({tab.count})
              </span>
            </button>
          ))}
        </div>

        <button
          className="btn btn-outline btn-sm"
          onClick={onRefresh}
          title="Refresh Deadlines"
        >
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Deadlines List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {sortedDeadlines.length === 0 ? (
          <div
            style={{
              background: '#FFFDF9',
              border: '1px solid #EBDCC8',
              borderRadius: '14px',
              padding: '36px 20px',
              textAlign: 'center',
              color: '#8C9A90',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <Calendar size={32} opacity={0.3} />
            <p style={{ fontSize: '13px', margin: 0 }}>
              {activeTab === 'all'
                ? 'No tracked obligations yet. Ingest an email, bill, or select a scenario!'
                : `No items found under "${activeTab.replace('_', ' ')}".`}
            </p>
          </div>
        ) : (
          sortedDeadlines.map((item) => {
            const daysDiff = getDaysDiff(item.candidate_date);
            const isDueSoon = daysDiff !== null && daysDiff >= 0 && daysDiff <= 3;
            const isOverdue = daysDiff !== null && daysDiff < 0;
            const isExpanded = expandedId === item.id;
            const details = nextStepData[item.id];

            return (
              <div
                key={item.id}
                style={{
                  background: '#FFFDF9',
                  border: '1px solid #EBDCC8',
                  borderLeft: isOverdue
                    ? '4px solid #EF4444'
                    : isDueSoon
                    ? '4px solid #D97706'
                    : item.status === 'completed'
                    ? '4px solid #10B981'
                    : '4px solid #000035',
                  borderRadius: '12px',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                {/* Main Row */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                    cursor: 'pointer'
                  }}
                  onClick={() => toggleExpand(item)}
                >
                  {/* Left Column: Provider & Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <h4
                        style={{
                          fontSize: '15px',
                          fontWeight: '700',
                          margin: 0,
                          color: '#000035',
                          textDecoration: item.status === 'completed' ? 'line-through' : 'none'
                        }}
                      >
                        {item.provider_name}
                      </h4>

                      <span className="status-pill blue" style={{ fontSize: '10px', padding: '2px 7px' }}>
                        {item.category}
                      </span>

                      <span style={{ fontSize: '11px', color: '#8C9A90', textTransform: 'lowercase' }}>
                        {item.obligation_type?.replace(/_/g, ' ')}
                      </span>

                      {/* Status Badge */}
                      <span
                        className={`status-pill ${
                          item.status === 'completed'
                            ? 'green'
                            : item.status === 'cancelled'
                            ? 'amber'
                            : item.status === 'upcoming'
                            ? 'blue'
                            : item.status === 'date_unverified'
                            ? 'amber'
                            : 'amber'
                        }`}
                        style={{ fontSize: '10px', padding: '2px 7px' }}
                      >
                        <span className="status-dot" />
                        <span>{item.status.replace(/_/g, ' ')}</span>
                      </span>
                    </div>

                    {/* Amount & Evidence Snippet Teaser */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
                      {item.amount !== null && item.amount !== undefined && (
                        <span style={{ fontSize: '13px', fontWeight: '700', color: '#000035' }}>
                          ₹{Number(item.amount).toLocaleString('en-IN')}
                        </span>
                      )}

                      <span
                        style={{
                          fontSize: '12px',
                          color: '#6B7280',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: '320px'
                        }}
                        title={item.evidence_snippet}
                      >
                        “{item.evidence_snippet}”
                      </span>
                    </div>
                  </div>

                  {/* Right Column: Date & Urgency Indicator */}
                  <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Calendar size={13} color="#8C9A90" />
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '13px',
                          fontWeight: '700',
                          color: item.candidate_date === 'UNVERIFIED' ? '#D97706' : '#000035'
                        }}
                      >
                        {item.candidate_date}
                      </span>
                    </div>

                    {daysDiff !== null && (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: '500',
                          color: isOverdue ? '#EF4444' : isDueSoon ? '#D9383A' : '#8C9A90'
                        }}
                      >
                        {daysDiff === 0
                          ? '⚡ Due Today'
                          : daysDiff === 1
                          ? '⏳ Due Tomorrow'
                          : daysDiff < 0
                          ? `⚠️ Overdue (${Math.abs(daysDiff)}d)`
                          : `in ${daysDiff} days`}
                      </span>
                    )}

                    <div style={{ marginTop: '2px', color: '#8C9A90' }}>
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </div>
                </div>

                {/* Expanded Action Checklist & Next Steps Drawer */}
                {isExpanded && (
                  <div
                    style={{
                      borderTop: '1px solid #EBDCC8',
                      paddingTop: '12px',
                      marginTop: '4px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}
                  >
                    {/* Action Guide / Instructions */}
                    <div
                      style={{
                        background: '#FFF9F0',
                        border: '1px solid #EBDCC8',
                        borderRadius: '10px',
                        padding: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#000035', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <ListOrdered size={14} color="#000035" />
                          Prepared Next-Step Action Guide
                        </span>

                        {item.official_url && (
                          <a
                            href={item.official_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-cream btn-sm"
                            style={{ fontSize: '11px', padding: '3px 8px', gap: '4px' }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span>Open Verified Portal</span>
                            <ExternalLink size={11} />
                          </a>
                        )}
                      </div>

                      {loadingNextStep[item.id] ? (
                        <div style={{ fontSize: '12px', color: '#8C9A90' }}>Loading action guide from MCP...</div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {(details?.checklist || [
                            item.next_step_instructions || 'Review the obligation details and follow through on the provider portal.'
                          ]).map((step, idx) => (
                            <div key={idx} style={{ fontSize: '12px', color: '#374151', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                              <span style={{ color: '#000035', fontWeight: '600' }}>•</span>
                              <span>{step}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Official Verification Notice */}
                      <div
                        style={{
                          marginTop: '10px',
                          paddingTop: '8px',
                          borderTop: '1px dashed #EBDCC8',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: '#8C9A90'
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <ShieldCheck size={12} color="#10B981" />
                          {item.official_url ? 'Validated Official Provider URL' : 'No Official Provider URL Available'}
                        </span>
                        <span style={{ fontStyle: 'italic' }}>
                          User action required on provider site
                        </span>
                      </div>
                    </div>

                    {/* Action Buttons Toolbar */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewEvidence(item);
                          }}
                        >
                          <FileSearch size={13} />
                          Inspect Evidence
                        </button>

                        <button
                          className="btn btn-outline btn-sm"
                          onClick={(e) => handleDownloadIcs(item.id, e)}
                          title="Download RFC 5545 iCalendar event"
                        >
                          <Download size={13} />
                          .ics Calendar
                        </button>
                      </div>

                      {/* Status Transition Controls */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {item.status !== 'completed' && (
                          <button
                            className="btn btn-navy btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onUpdateStatus(item.id, 'completed', 'Marked as completed / paid by user');
                            }}
                          >
                            <CheckCircle size={13} />
                            Mark Done
                          </button>
                        )}

                        {item.status !== 'cancelled' && (
                          <button
                            className="btn btn-outline btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onUpdateStatus(item.id, 'cancelled', 'Cancelled by user');
                            }}
                          >
                            <XCircle size={13} />
                            Mark Cancelled
                          </button>
                        )}

                        {item.status === 'completed' && (
                          <button
                            className="btn btn-outline btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onUpdateStatus(item.id, 'upcoming', 'Re-opened by user');
                            }}
                          >
                            Reopen
                          </button>
                        )}
                      </div>
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
