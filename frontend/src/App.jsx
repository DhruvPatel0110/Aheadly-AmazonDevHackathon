import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import SummaryCards from './components/SummaryCards';
import MountainArtwork from './components/MountainArtwork';
import PriorityDeadlinesCard from './components/PriorityDeadlinesCard';
import EvidenceNextStepCard from './components/EvidenceNextStepCard';
import McpActivityCard from './components/McpActivityCard';
import AssistantBar from './components/AssistantBar';
import SourceUploader from './components/SourceUploader';
import CandidateReviewCard from './components/CandidateReviewCard';
import DeadlineList from './components/DeadlineList';
import McpToolCallLog from './components/McpToolCallLog';
import EvidenceViewerModal from './components/EvidenceViewerModal';
import {
  Inbox,
  Calendar,
  Bell,
  Activity,
  Settings,
  Sparkles,
  RotateCcw,
  ShieldCheck,
  CheckCircle2,
  X,
  Plus
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('deadlines'); // 'deadlines' | 'sources' | 'reminders' | 'mcp' | 'settings'
  const [deadlines, setDeadlines] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [mcpLogs, setMcpLogs] = useState([]);
  const [candidateQueue, setCandidateQueue] = useState([]);
  const [selectedDeadline, setSelectedDeadline] = useState(null);
  const [selectedForEvidenceModal, setSelectedForEvidenceModal] = useState(null);
  const [evidenceSource, setEvidenceSource] = useState(null);
  const [isLoadingEvidenceSource, setIsLoadingEvidenceSource] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [isMcpOnline, setIsMcpOnline] = useState(true);

  // Assistant Chat states
  const [isTyping, setIsTyping] = useState(false);
  const [activeReply, setActiveReply] = useState(null);

  // 1. Fetch Deadlines
  const fetchDeadlines = useCallback(async () => {
    try {
      const res = await fetch('/api/deadlines');
      if (res.ok) {
        const data = await res.json();
        setDeadlines(data);

        // Pick initial selected deadline (prefer Netflix trial or first deadline)
        setSelectedDeadline((prev) => {
          if (prev && data.some((d) => d.id === prev.id)) {
            return data.find((d) => d.id === prev.id);
          }
          const netflixItem = data.find((d) => d.provider_name.toLowerCase().includes('netflix') && d.status === 'needs_review');
          return netflixItem || data[0] || null;
        });
      }
    } catch (err) {
      console.error('Error fetching deadlines:', err);
    }
  }, []);

  // 2. Fetch Stats (Derives truthful dashboard counts)
  const fetchStats = useCallback(async () => {
    try {
      setLoadingStats(true);
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats({
          total_tracked: data.total || 0,
          needs_review: (data.needs_review || 0) + (data.date_unverified || 0),
          upcoming: (data.upcoming || 0) + (data.confirmed || 0),
          confirmed: data.confirmed || 0,
          completed: data.completed || 0
        });
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  // 3. Fetch MCP Logs
  const fetchMcpLogs = useCallback(async () => {
    try {
      const res = await fetch('/api/mcp/log?limit=50');
      if (res.ok) {
        const data = await res.json();
        setMcpLogs(data);
        setIsMcpOnline(true);
      } else {
        setIsMcpOnline(false);
      }
    } catch (err) {
      setIsMcpOnline(false);
      console.error('Error fetching MCP logs:', err);
    }
  }, []);

  // Initial load & Polling (every 4s)
  useEffect(() => {
    fetchDeadlines();
    fetchStats();
    fetchMcpLogs();

    const interval = setInterval(() => {
      fetchMcpLogs();
      fetchStats();
      fetchDeadlines();
    }, 4000);

    return () => clearInterval(interval);
  }, [fetchDeadlines, fetchStats, fetchMcpLogs]);

  // Handle Source Ingestion
  const handleSourceIngested = (result) => {
    if (result.candidates && result.candidates.length > 0) {
      setCandidateQueue((prev) => {
        const existingIds = new Set(prev.map((c) => c.id));
        const newItems = result.candidates.filter((c) => !existingIds.has(c.id));
        return [...newItems, ...prev];
      });
      // Switch to sources view to review candidates or keep modal open
      setActiveTab('sources');
      setIsIngestModalOpen(false);
    }

    fetchDeadlines();
    fetchStats();
    fetchMcpLogs();
  };

  // Confirm Candidate via MCP tools
  const handleConfirmCandidate = async (candidateId, payload) => {
    try {
      await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'confirm_or_correct_deadline',
          arguments: {
            deadline_id: candidateId,
            confirmed_date: payload.confirmed_date,
            provider_name: payload.provider_name || ''
          }
        })
      });

      if (payload.confirmed_date && payload.confirmed_date !== 'UNVERIFIED') {
        await fetch('/api/mcp/call', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: 'create_follow_up',
            arguments: {
              deadline_id: candidateId,
              lead_days: payload.lead_days || [7, 1],
              export_calendar: false
            }
          })
        });
      }

      setCandidateQueue((prev) => prev.filter((c) => c.id !== candidateId));
      fetchDeadlines();
      fetchStats();
      fetchMcpLogs();
    } catch (err) {
      console.error('Failed to confirm candidate:', err);
    }
  };

  // Edit Candidate
  const handleEditCandidate = async (candidateId, payload) => {
    try {
      await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'confirm_or_correct_deadline',
          arguments: {
            deadline_id: candidateId,
            confirmed_date: payload.candidate_date,
            provider_name: payload.provider_name
          }
        })
      });

      setCandidateQueue((prev) =>
        prev.map((c) => (c.id === candidateId ? { ...c, ...payload } : c))
      );
      fetchDeadlines();
      fetchStats();
      fetchMcpLogs();
    } catch (err) {
      console.error('Failed to edit candidate:', err);
    }
  };

  // Open Evidence Modal with full source retrieval
  const handleOpenEvidenceModal = async (deadline) => {
    if (!deadline) return;
    setSelectedForEvidenceModal(deadline);
    setEvidenceSource(null);
    if (deadline.source_id) {
      setIsLoadingEvidenceSource(true);
      try {
        const res = await fetch(`/api/sources/${deadline.source_id}`);
        if (res.ok) {
          const data = await res.json();
          setEvidenceSource(data);
        } else {
          setEvidenceSource(null);
        }
      } catch (err) {
        console.error('Failed to fetch source for evidence modal:', err);
        setEvidenceSource(null);
      } finally {
        setIsLoadingEvidenceSource(false);
      }
    }
  };

  // Dismiss Candidate (Persists status='dismissed' via genuine MCP tool)
  const handleDismissCandidate = async (candidateId) => {
    try {
      const res = await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'update_deadline_status',
          arguments: {
            deadline_id: candidateId,
            new_status: 'dismissed',
            resolution_notes: 'Dismissed by user from candidate review queue'
          }
        })
      });
      if (res.ok) {
        setCandidateQueue((prev) => prev.filter((c) => c.id !== candidateId));
        fetchDeadlines();
        fetchStats();
        fetchMcpLogs();
      } else {
        console.error('Failed to dismiss candidate on server');
      }
    } catch (err) {
      console.error('Failed to dismiss candidate:', err);
    }
  };

  // Update Deadline Status via MCP tool
  const handleUpdateStatus = async (deadlineId, newStatus, notes) => {
    try {
      await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'update_deadline_status',
          arguments: {
            deadline_id: deadlineId,
            new_status: newStatus,
            resolution_notes: notes || ''
          }
        })
      });
      setSelectedDeadline((prev) => (prev && prev.id === deadlineId ? { ...prev, status: newStatus } : prev));
      fetchDeadlines();
      fetchStats();
      fetchMcpLogs();
    } catch (err) {
      console.error('Failed to update deadline status:', err);
    }
  };

  // 1. Mark Completed / Paid (Category-aware audit notes)
  const handleMarkCompleted = async (deadlineId) => {
    const item = deadlines.find((d) => d.id === deadlineId) || selectedDeadline;
    const isUtilityOrBill = ['utility_bill', 'insurance_premium', 'payment'].includes(item?.obligation_type);
    const note = isUtilityOrBill
      ? 'Payment marked completed by user'
      : 'Obligation marked resolved by user';
    await handleUpdateStatus(deadlineId, 'completed', note);
  };

  // 2. Cancel Subscription / Dismiss (Category-aware audit notes)
  const handleCancelSubscription = async (deadlineId) => {
    const item = deadlines.find((d) => d.id === deadlineId) || selectedDeadline;
    const isSub = ['subscription', 'free_trial'].includes(item?.obligation_type);
    const note = isSub
      ? 'Subscription cancelled by user'
      : 'Obligation cancelled/dismissed by user';
    await handleUpdateStatus(deadlineId, 'cancelled', note);
  };

  // 3. Remind Later
  const handleRemindLater = async (item) => {
    if (item.candidate_date === 'UNVERIFIED' || !item.candidate_date) {
      alert('Cannot schedule reminders for an unverified date. Please confirm the date first.');
      return;
    }
    try {
      await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'create_follow_up',
          arguments: {
            deadline_id: item.id,
            lead_days: [3, 1],
            export_calendar: false
          }
        })
      });
      await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'update_deadline_status',
          arguments: {
            deadline_id: item.id,
            new_status: 'upcoming',
            resolution_notes: 'Remind later scheduled (advance alerts configured 3d & 1d prior)'
          }
        })
      });
      fetchDeadlines();
      fetchStats();
      fetchMcpLogs();
    } catch (err) {
      console.error('Failed to schedule remind later:', err);
    }
  };

  // 4. Reopen
  const handleReopen = async (deadlineId) => {
    await handleUpdateStatus(deadlineId, 'upcoming', 'Reopened by user');
  };

  // Prepare next step
  const handlePrepareNextStep = async (deadlineId) => {
    try {
      const res = await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: 'prepare_next_step',
          arguments: { deadline_id: deadlineId }
        })
      });
      fetchMcpLogs();
      if (res.ok) return await res.json();
      return null;
    } catch (err) {
      console.error('Failed to fetch next steps:', err);
      return null;
    }
  };

  // Clear MCP Log
  const handleClearMcpLog = async () => {
    try {
      await fetch('/api/mcp/log', { method: 'DELETE' });
      setMcpLogs([]);
    } catch (err) {
      console.error('Failed to clear MCP logs:', err);
    }
  };

  // Reset Demo Data
  const handleResetDemo = async () => {
    if (!window.confirm('Reset all demo data and start with a clean state?')) return;
    try {
      await fetch('/api/demo/reset?confirm=true', {
        method: 'POST',
        headers: {
          'X-Confirm-Reset': 'confirm-reset',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ confirm: true })
      });
      setCandidateQueue([]);
      setDeadlines([]);
      setSelectedDeadline(null);
      setMcpLogs([]);
      fetchStats();
      fetchDeadlines();
      fetchMcpLogs();
    } catch (err) {
      console.error('Failed to reset demo:', err);
    }
  };

  // Assistant Query Handler
  const handleAssistantSubmit = async (queryText) => {
    setIsTyping(true);
    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: queryText,
          active_deadline_id: selectedDeadline?.id || null
        })
      });
      const data = await res.json();
      setActiveReply(data);
      fetchDeadlines();
      fetchStats();
      fetchMcpLogs();
    } catch (err) {
      setActiveReply({ reply: `Error: ${err.message}` });
    } finally {
      setIsTyping(false);
    }
  };

  // Filter deadlines based on search input
  const filteredDeadlines = useMemo(() => {
    if (!searchQuery.trim()) return deadlines;
    const q = searchQuery.toLowerCase();
    return deadlines.filter(
      (d) =>
        d.provider_name?.toLowerCase().includes(q) ||
        d.category?.toLowerCase().includes(q) ||
        d.evidence_snippet?.toLowerCase().includes(q)
    );
  }, [deadlines, searchQuery]);

  return (
    <div className="app-layout">
      {/* Left Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        onOpenIngest={() => setIsIngestModalOpen(true)}
        isMcpOnline={isMcpOnline}
      />

      {/* Main App Content Wrapper */}
      <div className="main-wrapper">
        {/* Top Header */}
        <Header
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          notificationCount={stats?.needs_review || 0}
        />

        {/* Dynamic Tab Body */}
        <div className="dashboard-content">
          {/* TAB 1: DEADLINES (Unified Primary View with KPI Cards & Actions) */}
          {activeTab === 'deadlines' && (
            <>
              {/* Dashboard Intro Headline & Mountain Artwork */}
              <section className="dashboard-intro">
                <div className="dashboard-title-box">
                  <h1 className="dashboard-title">
                    Your obligations, under control.
                  </h1>
                  <p className="dashboard-subtitle">
                    Find the deadline. Verify the evidence. Follow through.
                  </p>
                </div>
                <MountainArtwork />
              </section>

              {/* 4 Summary Statistics Cards */}
              <SummaryCards stats={stats} loading={loadingStats} />

              {/* Two-Column Grid: Deadlines & Evidence/MCP Cards */}
              <div className="dashboard-grid">
                {/* Left / Center Column: Priority Deadlines & Assistant Input */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <PriorityDeadlinesCard
                    deadlines={filteredDeadlines}
                    selectedId={selectedDeadline?.id}
                    onSelectDeadline={(item) => setSelectedDeadline(item)}
                    onMarkCompleted={handleMarkCompleted}
                    onRemindLater={handleRemindLater}
                    onCancelSubscription={handleCancelSubscription}
                    onReopen={handleReopen}
                    onInspectEvidence={handleOpenEvidenceModal}
                  />

                  {/* Assistant Input Bar */}
                  <AssistantBar
                    onChatSubmit={handleAssistantSubmit}
                    isTyping={isTyping}
                    activeReply={activeReply}
                    onCloseReply={() => setActiveReply(null)}
                  />
                </div>

                {/* Right Column: Evidence & Next Step + Live MCP Activity */}
                <div className="right-column">
                  <EvidenceNextStepCard
                    deadline={selectedDeadline}
                    onOpenFullEvidence={handleOpenEvidenceModal}
                    onPrepareNextStep={handlePrepareNextStep}
                    onMarkCompleted={handleMarkCompleted}
                    onRemindLater={handleRemindLater}
                    onCancelSubscription={handleCancelSubscription}
                    onReopen={handleReopen}
                  />

                  <McpActivityCard
                    logs={mcpLogs}
                    onViewFullLog={() => setActiveTab('mcp')}
                  />
                </div>
              </div>
            </>
          )}

          {/* TAB 2: SOURCES & CANDIDATE QUEUE */}
          {activeTab === 'sources' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#000035', margin: '0 0 4px' }}>
                  Document Ingestion & Scenarios
                </h2>
                <p style={{ fontSize: '13.5px', color: '#78736B', margin: 0 }}>
                  Upload bills, paste emails, or trigger 1-click test scenarios to extract obligations with verbatim evidence.
                </p>
              </div>

              {/* Candidate Review Queue (if newly ingested candidates exist) */}
              {candidateQueue.length > 0 && (
                <div style={{ background: '#FFFDF9', border: '1px solid #EBDCC8', borderRadius: '16px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="status-dot" style={{ backgroundColor: '#D97706', width: '8px', height: '8px' }} />
                      <h3 style={{ fontSize: '15.5px', fontWeight: '700', color: '#000035', margin: 0 }}>
                        Candidate Review Queue ({candidateQueue.length})
                      </h3>
                    </div>
                    <span style={{ fontSize: '12px', color: '#8C9A90' }}>
                      Evidence grounded • Please confirm or amend
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {candidateQueue.map((cand) => (
                      <CandidateReviewCard
                        key={cand.id}
                        candidate={cand}
                        onConfirm={handleConfirmCandidate}
                        onEdit={handleEditCandidate}
                        onDismiss={handleDismissCandidate}
                        onViewEvidence={handleOpenEvidenceModal}
                      />
                    ))}
                  </div>
                </div>
              )}

              <div className="card" style={{ padding: '20px' }}>
                <SourceUploader onSourceIngested={handleSourceIngested} />
              </div>
            </div>
          )}

          {/* TAB 4: REMINDERS */}
          {activeTab === 'reminders' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#000035', margin: '0 0 4px' }}>
                  Scheduled Advance Alerts
                </h2>
                <p style={{ fontSize: '13.5px', color: '#78736B', margin: 0 }}>
                  In-app notifications scheduled at 7 days, 3 days, and 1 day prior to avoid billing surprises.
                </p>
              </div>

              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {deadlines
                    .filter((d) => d.status === 'upcoming' || d.status === 'confirmed')
                    .map((d) => (
                      <div
                        key={d.id}
                        style={{
                          background: '#FFF9F0',
                          border: '1px solid #EBDCC8',
                          borderRadius: '10px',
                          padding: '12px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <Bell size={18} color="#000035" />
                          <div>
                            <div style={{ fontSize: '14px', fontWeight: '700', color: '#000035' }}>
                              {d.provider_name}
                            </div>
                            <div style={{ fontSize: '12px', color: '#8C9A90' }}>
                              Due on {d.candidate_date} • Alert configured 3 days prior
                            </div>
                          </div>
                        </div>

                        <a
                          href={`/api/deadlines/${d.id}/ics`}
                          className="btn btn-outline btn-sm"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Download .ics
                        </a>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: MCP ACTIVITY */}
          {activeTab === 'mcp' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#000035', margin: '0 0 4px' }}>
                  Live MCP Protocol Inspector
                </h2>
                <p style={{ fontSize: '13.5px', color: '#78736B', margin: 0 }}>
                  Observability console for judges: real JSON-RPC 2.0 tool calls over Streamable HTTP (Spec 2025-11-25+).
                </p>
              </div>

              <div className="card" style={{ minHeight: '500px' }}>
                <McpToolCallLog
                  logs={mcpLogs}
                  onRefresh={fetchMcpLogs}
                  onClear={handleClearMcpLog}
                />
              </div>
            </div>
          )}

          {/* TAB 6: SETTINGS */}
          {activeTab === 'settings' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '680px' }}>
              <div>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#000035', margin: '0 0 4px' }}>
                  Application Settings & System
                </h2>
                <p style={{ fontSize: '13.5px', color: '#78736B', margin: 0 }}>
                  Configuration, track information, and demo state management.
                </p>
              </div>

              <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid #EBDCC8' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: '700', color: '#000035' }}>
                      Hackathon Track
                    </div>
                    <div style={{ fontSize: '12px', color: '#8C9A90' }}>
                      Amazon Developer Hackathon — Alexa+ Track
                    </div>
                  </div>
                  <span className="status-pill blue">Alexa+</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid #EBDCC8' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: '700', color: '#000035' }}>
                      Budget Mode
                    </div>
                    <div style={{ fontSize: '12px', color: '#8C9A90' }}>
                      Strict ₹0 out-of-pocket baseline (Local SQLite + Deterministic engine)
                    </div>
                  </div>
                  <span className="status-pill green">₹0 Active</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: '700', color: '#000035' }}>
                      Reset Demo State
                    </div>
                    <div style={{ fontSize: '12px', color: '#8C9A90' }}>
                      Wipe database and clear MCP logs for a clean demonstration run.
                    </div>
                  </div>
                  <button className="btn btn-cream btn-sm" onClick={handleResetDemo}>
                    <RotateCcw size={13} />
                    <span>Reset Data</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* QUICK INGEST MODAL */}
      {isIngestModalOpen && (
        <div className="modal-overlay" onClick={() => setIsIngestModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Plus size={18} color="#000035" />
                <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#000035', margin: 0 }}>
                  Ingest New Source Document
                </h3>
              </div>
              <button
                className="btn btn-outline"
                style={{ padding: '5px', borderRadius: '50%' }}
                onClick={() => setIsIngestModalOpen(false)}
              >
                <X size={15} />
              </button>
            </div>
            <div className="modal-body">
              <SourceUploader onSourceIngested={handleSourceIngested} />
            </div>
          </div>
        </div>
      )}

      {/* EVIDENCE GROUNDING MODAL */}
      {selectedForEvidenceModal && (
        <EvidenceViewerModal
          deadline={selectedForEvidenceModal}
          source={evidenceSource}
          onClose={() => {
            setSelectedForEvidenceModal(null);
            setEvidenceSource(null);
          }}
        />
      )}
    </div>
  );
}
