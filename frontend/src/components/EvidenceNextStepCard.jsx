import React, { useState, useEffect } from 'react';
import {
  FileText,
  Calendar,
  ExternalLink,
  MoreHorizontal,
  ChevronRight,
  Shield,
  Radio,
  Zap,
  CheckCircle2,
  XCircle,
  Bell,
  RotateCcw,
  Loader2
} from 'lucide-react';

function ProviderAvatarSmall({ name = '', category = '' }) {
  const lower = name.toLowerCase();
  if (lower.includes('netflix')) {
    return (
      <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: '#000000' }}>
        <span style={{ color: '#E50914', fontWeight: '900', fontSize: '16px', fontFamily: 'Impact, sans-serif' }}>N</span>
      </div>
    );
  }
  if (lower.includes('hdfc')) {
    return (
      <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: '#D61B23', padding: '2px' }}>
        <span style={{ color: '#FFFFFF', fontSize: '8px', fontWeight: '900' }}>HDFC</span>
      </div>
    );
  }
  if (lower.includes('airtel')) {
    return (
      <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: '#E60000' }}>
        <span style={{ color: '#FFFFFF', fontWeight: '900', fontSize: '10px' }}>airtel</span>
      </div>
    );
  }
  if (lower.includes('spotify')) {
    return (
      <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: '#1DB954' }}>
        <Radio size={16} color="#FFFFFF" />
      </div>
    );
  }
  if (lower.includes('cred')) {
    return (
      <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: '#121212' }}>
        <Shield size={16} color="#FFFFFF" />
      </div>
    );
  }

  const bg = category === 'insurance' ? '#D61B23' : category === 'utility' ? '#0F52BA' : '#2A2C38';
  return (
    <div className="provider-logo-box" style={{ width: '36px', height: '36px', background: bg }}>
      <span style={{ fontSize: '12px', fontWeight: '700' }}>{name ? name.slice(0, 2).toUpperCase() : 'DL'}</span>
    </div>
  );
}

function formatDateLong(dateStr) {
  if (!dateStr || dateStr === 'UNVERIFIED') return 'Date Unverified';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function EvidenceNextStepCard({
  deadline,
  onOpenFullEvidence,
  onMarkCompleted,
  onRemindLater,
  onCancelSubscription,
  onReopen,
  onPrepareNextStep
}) {
  const [nextStepData, setNextStepData] = useState(null);
  const [isLoadingNextStep, setIsLoadingNextStep] = useState(false);

  useEffect(() => {
    if (!deadline?.id) {
      setNextStepData(null);
      return;
    }

    let isMounted = true;
    setIsLoadingNextStep(true);

    const fetchNextSteps = async () => {
      try {
        let data = null;
        if (onPrepareNextStep) {
          data = await onPrepareNextStep(deadline.id);
        } else {
          const res = await fetch('/api/mcp/call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              tool: 'prepare_next_step',
              arguments: { deadline_id: deadline.id }
            })
          });
          if (res.ok) data = await res.json();
        }
        if (isMounted && data) {
          setNextStepData(data);
        }
      } catch (err) {
        console.error('Failed to load next steps for deadline:', err);
      } finally {
        if (isMounted) setIsLoadingNextStep(false);
      }
    };

    fetchNextSteps();

    return () => {
      isMounted = false;
    };
  }, [deadline?.id, onPrepareNextStep]);

  if (!deadline) {
    return (
      <div className="evidence-card" style={{ textAlign: 'center', color: '#8C9A90', padding: '36px 20px' }}>
        <FileText size={28} opacity={0.4} style={{ margin: '0 auto 8px' }} />
        <p style={{ fontSize: '13px' }}>Select an obligation to inspect verbatim evidence and next steps.</p>
      </div>
    );
  }

  const isVerified = deadline.verification_status === 'user_confirmed' || deadline.status === 'confirmed';
  const isReview = deadline.status === 'needs_review' || deadline.status === 'date_unverified';
  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled' || deadline.status === 'dismissed';

  // Category and obligation type distinctions
  const isSubscription = deadline.category === 'subscription' || deadline.obligation_type === 'trial_ending';
  const isPaymentObligation = deadline.category === 'utility' || deadline.category === 'broadband' || deadline.obligation_type === 'payment_due';

  const markDoneLabel = isPaymentObligation ? 'Mark Paid' : 'Completed';
  const cancelBtnLabel = isSubscription ? 'Cancel Subscription' : 'Dismiss / Cancel';

  // Extract date snippet highlighting
  const snippet = deadline.evidence_snippet || 'Document evidence not available.';
  const dateStr = deadline.original_date_str || deadline.candidate_date;

  let renderedSnippet = snippet;
  if (dateStr && snippet.includes(dateStr)) {
    const parts = snippet.split(dateStr);
    renderedSnippet = (
      <>
        {parts[0]}
        <mark>{dateStr}</mark>
        {parts.slice(1).join(dateStr)}
      </>
    );
  }

  // Use checklist from genuine MCP prepare_next_step tool execution
  const checklistItems = nextStepData?.checklist || (
    isSubscription
      ? [
          'Confirm cancellation deadline from source document.',
          'Navigate to official provider subscription portal.',
          'Complete cancellation before renewal or trial conversion.',
          'Verify cancellation confirmation email.'
        ]
      : [
          'Review bill summary and account identifier.',
          'Navigate to official provider bill payment portal.',
          'Complete payment to prevent service interruption.',
          'Mark obligation completed upon payment receipt.'
        ]
  );

  const officialUrl = nextStepData?.official_url || deadline.official_url;
  const hasVerifiedUrl = Boolean(officialUrl);

  return (
    <div className="evidence-card">
      {/* Header */}
      <div className="evidence-header">
        <div className="evidence-title">
          <FileText size={17} color="#000035" />
          <span>Evidence & next step</span>
        </div>
        <button className="header-icon-btn" title="More options">
          <MoreHorizontal size={18} color="#8C9A90" />
        </button>
      </div>

      {/* Selected Provider Info */}
      <div className="evidence-provider-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ProviderAvatarSmall name={deadline.provider_name} category={deadline.category} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#000035' }}>
              {deadline.provider_name}
            </div>
            <div style={{ fontSize: '12px', color: '#8C9A90', textTransform: 'capitalize' }}>
              {deadline.category || 'Subscription'}
            </div>
          </div>
        </div>

        {/* Status Pill */}
        <div>
          {isCompleted ? (
            <span className="status-pill green">
              <span className="status-dot" />
              <span>Completed</span>
            </span>
          ) : isCancelled ? (
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
      </div>

      {/* Date Box */}
      <div className="evidence-date-box">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={15} color="#000035" />
          <span style={{ fontSize: '13px', fontWeight: '600', color: '#000035' }}>
            {formatDateLong(deadline.candidate_date)}
          </span>
        </div>
        <span
          style={{
            fontSize: '11px',
            color: isCompleted ? '#10B981' : isCancelled ? '#6B7280' : '#D9383A',
            fontWeight: '600'
          }}
        >
          {isCompleted
            ? '✓ Payment Completed'
            : isCancelled
            ? '✕ Resolved'
            : deadline.obligation_type === 'trial_ending'
            ? 'Trial ending soon'
            : deadline.obligation_type === 'renewal'
            ? 'Renewal date'
            : 'Payment due'}
        </span>
      </div>

      {/* Source Excerpt */}
      <div className="evidence-excerpt-section">
        <span className="evidence-section-label">Source excerpt (from document)</span>
        <div className="evidence-quote-box">
          <span style={{ color: '#8C9A90', fontSize: '16px', lineHeight: '0', verticalAlign: '-3px', marginRight: '4px' }}>
            “
          </span>
          {renderedSnippet}
          <span style={{ color: '#8C9A90', fontSize: '16px', lineHeight: '0', verticalAlign: '-3px', marginLeft: '4px' }}>
            ”
          </span>
        </div>
      </div>

      {/* Recommended Next Step (from genuine MCP prepare_next_step tool) */}
      <div className="evidence-excerpt-section">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span className="evidence-section-label" style={{ margin: 0 }}>Recommended next step (MCP)</span>
          {isLoadingNextStep && (
            <span style={{ fontSize: '11px', color: '#8C9A90', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Loader2 size={11} className="spin" /> loading...
            </span>
          )}
        </div>

        {/* Verified URL Banner */}
        {hasVerifiedUrl ? (
          <div style={{ marginBottom: '8px', padding: '6px 10px', background: '#E7F7ED', border: '1px solid #A7F3D0', borderRadius: '6px', fontSize: '11.5px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: '#065F46', fontWeight: '600' }}>Official Provider Portal:</span>
            <a href={officialUrl} target="_blank" rel="noopener noreferrer" style={{ color: '#047857', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: '700', textDecoration: 'underline' }}>
              <span>Visit Link</span>
              <ExternalLink size={12} />
            </a>
          </div>
        ) : (
          <div style={{ marginBottom: '8px', padding: '5px 8px', background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '6px', fontSize: '11px', color: '#8C9A90' }}>
            No verified portal link on record for {deadline.provider_name}.
          </div>
        )}

        <div className="checklist-container">
          {checklistItems.map((item, idx) => (
            <div key={idx} className="checklist-item">
              <div className={`checklist-circle ${isCompleted || isCancelled ? 'checked' : ''}`} />
              <div style={{ fontSize: '12px' }}>{item}</div>
            </div>
          ))}
        </div>

        {nextStepData?.safety_notice && (
          <div style={{ marginTop: '6px', fontSize: '10.5px', color: '#8C9A90', fontStyle: 'italic' }}>
            {nextStepData.safety_notice}
          </div>
        )}
      </div>

      {/* Action Buttons: Completed, Remind Later, Cancel / Dismiss */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {!isCompleted ? (
            <button
              className="btn btn-navy btn-sm"
              style={{ justifyContent: 'center', gap: '6px', fontSize: '12px', padding: '6px 10px' }}
              onClick={() => onMarkCompleted && onMarkCompleted(deadline.id)}
            >
              <CheckCircle2 size={13} color="#10B981" />
              <span>{markDoneLabel}</span>
            </button>
          ) : (
            <button
              className="btn btn-outline btn-sm"
              style={{ justifyContent: 'center', gap: '6px', fontSize: '12px', padding: '6px 10px' }}
              onClick={() => onReopen && onReopen(deadline.id)}
            >
              <RotateCcw size={13} />
              <span>Reopen</span>
            </button>
          )}

          <button
            className="btn btn-outline btn-sm"
            style={{
              justifyContent: 'center',
              gap: '6px',
              fontSize: '12px',
              padding: '6px 10px',
              borderColor: '#D97706',
              color: '#B45309'
            }}
            onClick={() => onRemindLater && onRemindLater(deadline)}
          >
            <Bell size={13} />
            <span>Remind Later</span>
          </button>
        </div>

        {!isCancelled ? (
          <button
            className="btn btn-outline btn-sm"
            style={{
              width: '100%',
              justifyContent: 'center',
              gap: '6px',
              fontSize: '12px',
              padding: '6px 10px',
              borderColor: '#DC2626',
              color: '#DC2626'
            }}
            onClick={() => onCancelSubscription && onCancelSubscription(deadline.id)}
          >
            <XCircle size={13} />
            <span>{cancelBtnLabel}</span>
          </button>
        ) : (
          <div style={{ textAlign: 'center', fontSize: '11.5px', color: '#6B7280', fontStyle: 'italic', padding: '3px' }}>
            {isSubscription ? 'Subscription Marked as Cancelled' : 'Obligation Cancelled / Dismissed'}
          </div>
        )}
      </div>

      {/* Primary Action Button */}
      <button className="btn-open-evidence" onClick={() => onOpenFullEvidence(deadline)} style={{ marginTop: '4px' }}>
        <ExternalLink size={14} />
        <span>Open full evidence</span>
        <ChevronRight size={14} />
      </button>
    </div>
  );
}
