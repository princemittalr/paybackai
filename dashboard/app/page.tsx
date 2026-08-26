'use client';
import { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  Tooltip, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Hooks ──────────────────────────────────────────────
function useCountUp(target: number, duration = 1200) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!target) return;
    const start = Date.now();
    const tick = () => {
      const p = Math.min((Date.now() - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setValue(Math.floor(target * ease));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);
  return value;
}

// ── Components ─────────────────────────────────────────
const Badge = ({ status }: { status: string }) => {
  const map: Record<string, string> = {
    recovered: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    failed_recovery: 'bg-rose-500/15 text-rose-400 border-rose-500/25',
    skipped: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
    pending: 'bg-slate-500/15 text-slate-400 border-slate-500/25',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono border ${map[status] || map.pending}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

const ScenarioBadge = ({ type }: { type: string }) => {
  const map: Record<string, { label: string; color: string }> = {
    payment_failure: { label: '💳 Payment', color: 'text-blue-400' },
    checkout_abandonment: { label: '🛒 Cart', color: 'text-purple-400' },
    subscription_failure: { label: '🔄 Subscription', color: 'text-orange-400' },
  };
  const item = map[type] || { label: type, color: 'text-slate-400' };
  return <span className={`text-xs font-mono ${item.color}`}>{item.label}</span>;
};

const AuditDrawer = ({ paymentId, data, onClose }: any) => {
  if (!paymentId) return null;
  const eventColors: Record<string, string> = {
    PROCESSING_STARTED: '#3B82F6',
    CLASSIFIED: '#8B5CF6',
    INTERVENTION_SELECTED: '#F59E0B',
    EMAIL_SENT: '#10B981',
    SMS_SENT: '#10B981',
    WHATSAPP_SENT: '#10B981',
    CART_RECOVERY_SENT: '#06B6D4',
    MANDATE_RETRY_ATTEMPTED: '#F97316',
    BLACKLISTED: '#F43F5E',
    STOPPED_BY_RULES: '#F97316',
    PROCESSING_COMPLETE: '#10B981',
  };
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end">
      <div className="bg-[#0D1117] border-l border-slate-800 w-full max-w-lg h-full overflow-y-auto">
        <div className="sticky top-0 bg-[#0D1117] border-b border-slate-800 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 font-mono mb-1">AUDIT TRAIL</p>
            <p className="text-xs font-mono text-slate-300 truncate">{paymentId}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl transition-colors">✕</button>
        </div>
        <div className="px-6 py-6 space-y-6">
          <div>
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Event Timeline</p>
            <div className="space-y-0">
              {data?.audit_trail?.map((event: any, i: number) => (
                <div key={event.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-2 h-2 rounded-full mt-2 flex-shrink-0"
                      style={{ backgroundColor: eventColors[event.event_type] || '#64748B' }} />
                    {i < (data?.audit_trail?.length - 1) && <div className="w-px flex-1 bg-slate-800 mt-1" />}
                  </div>
                  <div className="pb-4 flex-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-mono font-semibold text-slate-300">{event.event_type}</span>
                      <span className="text-xs text-slate-600">{new Date(event.timestamp).toLocaleTimeString()}</span>
                    </div>
                    {event.reasoning && <p className="text-xs text-slate-500 mt-1 leading-relaxed">{event.reasoning}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
          {data?.recovery_actions?.length > 0 && (
            <div>
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Recovery Actions</p>
              <div className="space-y-3">
                {data.recovery_actions.map((action: any) => (
                  <div key={action.id} className="bg-slate-900 rounded-lg p-4 border border-slate-800">
                    <div className="flex justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-slate-200">{action.action_type}</span>
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${
                        action.outcome?.includes('DISPATCHED') || action.outcome === 'SUCCESS' || action.outcome?.includes('QUEUED')
                          ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'
                      }`}>{action.outcome}</span>
                    </div>
                    <p className="text-xs text-slate-500">{action.decision_explanation}</p>
                    {action.outcome_detail && <p className="text-xs text-slate-600 mt-1 font-mono">{action.outcome_detail}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Dashboard ──────────────────────────────────────────
export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [selectedPayment, setSelectedPayment] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<any>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [scenarioFilter, setScenarioFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'scenarios' | 'interventions' | 'promises' | 'payments'>('overview');
  const [runningBatch, setRunningBatch] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '80' });
      if (statusFilter) params.append('status', statusFilter);
      if (scenarioFilter) params.append('scenario_type', scenarioFilter);

      const [sRes, pRes] = await Promise.all([
        fetch(`${API}/api/stats`),
        fetch(`${API}/api/payments?${params}`)
      ]);
      const [sData, pData] = await Promise.all([sRes.json(), pRes.json()]);
      setStats(sData);
      setPayments(pData.payments || []);
      setLastUpdated(new Date());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [statusFilter, scenarioFilter]);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => {
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleRunBatch = async () => {
    setRunningBatch(true);
    try {
      await fetch(`${API}/api/admin/run-batch?limit=80`, { method: 'POST' });
      await fetchAll();
    } finally {
      setRunningBatch(false);
    }
  };

  const handleSelectPayment = async (id: string) => {
    setSelectedPayment(id);
    const res = await fetch(`${API}/api/payments/${id}/audit`);
    setAuditData(await res.json());
  };

  const summary = stats?.summary || {};
  const scenarioBreakdown = stats?.scenario_breakdown || {};
  const interventionStats = stats?.intervention_effectiveness || [];
  const promiseTracker = stats?.promise_tracker || {};
  const recentRuns = stats?.recent_runs || [];

  const recoveredCount = useCountUp(summary.recovered || 0);
  const amountRecovered = useCountUp(Math.floor(summary.total_amount_recovered_rupees || 0));
  const amountAtRisk = useCountUp(Math.floor(summary.total_amount_at_risk_rupees || 0));

  // Chart data
  const pieData = [
    { name: 'Recovered', value: summary.recovered || 0, color: '#10B981' },
    { name: 'Failed', value: summary.failed_recovery || 0, color: '#F43F5E' },
    { name: 'Skipped', value: summary.skipped || 0, color: '#F59E0B' },
    { name: 'Pending', value: summary.pending || 0, color: '#475569' },
  ];

  const scenarioChartData = [
    {
      name: '💳 Payment Failures',
      total: scenarioBreakdown.payment_failure?.total || 0,
      recovered: scenarioBreakdown.payment_failure?.recovered || 0,
      amount: Math.floor((scenarioBreakdown.payment_failure?.amount_recovered || 0) / 100),
    },
    {
      name: '🛒 Cart Abandoned',
      total: scenarioBreakdown.checkout_abandonment?.total || 0,
      recovered: scenarioBreakdown.checkout_abandonment?.recovered || 0,
      amount: Math.floor((scenarioBreakdown.checkout_abandonment?.amount_recovered || 0) / 100),
    },
    {
      name: '🔄 Subscriptions',
      total: scenarioBreakdown.subscription_failure?.total || 0,
      recovered: scenarioBreakdown.subscription_failure?.recovered || 0,
      amount: Math.floor((scenarioBreakdown.subscription_failure?.amount_recovered || 0) / 100),
    },
  ];

  const interventionChartData = interventionStats.map((i: any) => ({
    name: i.action_type.replace('SEND_', '').replace('_', ' '),
    total: i.total,
    successful: i.successful,
    rate: i.total > 0 ? Math.round((i.successful / i.total) * 100) : 0,
  }));

  const areaData = recentRuns
    .filter((r: any) => r.status === 'completed' && r.total_payments > 0)
    .reverse()
    .map((run: any, i: number) => ({
      name: `Run ${i + 1}`,
      recovered: run.recovered,
      failed: run.failed_recovery,
      amount: Math.floor(run.total_amount_recovered / 100),
    }));

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'scenarios', label: 'Scenarios' },
    { id: 'interventions', label: 'Interventions' },
    { id: 'promises', label: `Promises (${promiseTracker.total || 0})` },
    { id: 'payments', label: `Payments (${summary.total_payments || 0})` },
  ];

  if (loading) return (
    <div className="min-h-screen bg-[#0A0F1E] flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-slate-500 text-sm font-mono">Connecting to PaybackAI...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0A0F1E] text-slate-100">

      {/* Header */}
      <header className="border-b border-slate-800/60 bg-[#0A0F1E]/90 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-blue-700 rounded flex items-center justify-center">
              <span className="text-white text-xs font-bold">P</span>
            </div>
            <span className="font-semibold text-white">PaybackAI</span>
            <span className="text-slate-600 text-xs hidden sm:block">/ Recovery Dashboard</span>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-xs text-slate-600 font-mono hidden md:block">
                {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={handleRunBatch}
              disabled={runningBatch}
              className="text-xs font-mono bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1.5 rounded transition-colors"
            >
              {runningBatch ? '⟳ Running...' : '▶ Run Batch'}
            </button>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-xs text-emerald-400 font-mono">LIVE</span>
            </div>
            <button onClick={fetchAll} className="text-xs text-slate-500 hover:text-white font-mono border border-slate-800 hover:border-slate-600 px-3 py-1.5 rounded transition-colors">
              ↻
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">

        {/* Hero metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'RECOVERY RATE', value: `${summary.recovery_rate || 0}%`, sub: `${recoveredCount} of ${summary.total_payments || 0} payments`, accent: 'text-emerald-400', border: 'border-emerald-500/20', bg: 'bg-emerald-500/5' },
            { label: 'AMOUNT RECOVERED', value: `₹${amountRecovered.toLocaleString('en-IN')}`, sub: 'Across all scenarios', accent: 'text-blue-400', border: 'border-blue-500/20', bg: 'bg-blue-500/5' },
            { label: 'TOTAL AT RISK', value: `₹${amountAtRisk.toLocaleString('en-IN')}`, sub: 'Failed payment value', accent: 'text-rose-400', border: 'border-rose-500/20', bg: 'bg-rose-500/5' },
            { label: 'PROMISES TRACKED', value: promiseTracker.total || 0, sub: `${promiseTracker.pending || 0} pending follow-up`, accent: 'text-amber-400', border: 'border-amber-500/20', bg: 'bg-amber-500/5' },
          ].map((card) => (
            <div key={card.label} className={`rounded-xl border ${card.border} ${card.bg} p-5`}>
              <p className="text-xs font-mono text-slate-500 tracking-widest mb-3">{card.label}</p>
              <p className={`text-2xl lg:text-3xl font-mono font-bold ${card.accent}`}>{card.value}</p>
              <p className="text-xs text-slate-600 mt-2">{card.sub}</p>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-800">
          <div className="flex gap-0">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 text-xs font-mono transition-colors border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? 'text-blue-400 border-blue-500'
                    : 'text-slate-500 border-transparent hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-3 bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Recovery Trend</p>
                {areaData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={areaData}>
                      <defs>
                        <linearGradient id="gRec" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gFail" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#F43F5E" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                      <Tooltip contentStyle={{ background: '#0D1117', border: '1px solid #1E293B', borderRadius: 8, fontSize: 12 }} />
                      <Area type="monotone" dataKey="recovered" stroke="#10B981" fill="url(#gRec)" strokeWidth={2} name="Recovered" />
                      <Area type="monotone" dataKey="failed" stroke="#F43F5E" fill="url(#gFail)" strokeWidth={2} name="Failed" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-48 flex items-center justify-center text-slate-600 text-sm">No completed runs yet</div>
                )}
              </div>
              <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Outcome Breakdown</p>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#0D1117', border: '1px solid #1E293B', borderRadius: 8, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {pieData.map((d) => (
                    <div key={d.name} className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                      <span className="text-xs text-slate-500">{d.name}</span>
                      <span className="text-xs font-mono text-slate-300 ml-auto">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Batch runs */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Batch Run History</p>
              {recentRuns.filter((r: any) => r.total_payments > 0).length === 0 ? (
                <p className="text-slate-600 text-sm text-center py-4">No completed runs yet — click Run Batch</p>
              ) : (
                <div className="space-y-2">
                  {recentRuns.filter((r: any) => r.total_payments > 0).map((run: any) => {
                    const rate = run.total_payments > 0 ? Math.round(run.recovered / run.total_payments * 100) : 0;
                    return (
                      <div key={run.run_id} className="flex items-center gap-4 p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono text-slate-400 truncate">{run.run_id}</p>
                          <p className="text-xs text-slate-600 mt-0.5">{new Date(run.started_at).toLocaleString()}</p>
                        </div>
                        <div className="hidden md:flex items-center gap-6 text-right">
                          <div><p className="text-xs text-slate-500">Total</p><p className="text-sm font-mono text-slate-200">{run.total_payments}</p></div>
                          <div><p className="text-xs text-slate-500">Recovered</p><p className="text-sm font-mono text-emerald-400">{run.recovered}</p></div>
                          <div><p className="text-xs text-slate-500">Rate</p><p className="text-sm font-mono text-blue-400">{rate}%</p></div>
                          <div><p className="text-xs text-slate-500">Amount</p><p className="text-sm font-mono text-slate-200">₹{Math.floor(run.total_amount_recovered / 100).toLocaleString('en-IN')}</p></div>
                        </div>
                        <span className={`text-xs font-mono px-2 py-1 rounded ${run.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          {run.status}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* SCENARIOS TAB */}
        {activeTab === 'scenarios' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {scenarioChartData.map((s) => {
                const rate = s.total > 0 ? Math.round((s.recovered / s.total) * 100) : 0;
                return (
                  <div key={s.name} className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
                    <p className="text-sm font-mono text-slate-300 mb-4">{s.name}</p>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">Total</span>
                        <span className="text-xs font-mono text-slate-300">{s.total}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">Recovered</span>
                        <span className="text-xs font-mono text-emerald-400">{s.recovered}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">Rate</span>
                        <span className="text-xs font-mono text-blue-400">{rate}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">Amount</span>
                        <span className="text-xs font-mono text-slate-200">₹{s.amount.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2">
                        <div
                          className="bg-emerald-500 h-1.5 rounded-full transition-all duration-1000"
                          style={{ width: `${rate}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Recovery by Scenario</p>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={scenarioChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} width={120} />
                  <Tooltip contentStyle={{ background: '#0D1117', border: '1px solid #1E293B', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="total" fill="#1E293B" name="Total" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="recovered" fill="#10B981" name="Recovered" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* INTERVENTIONS TAB */}
        {activeTab === 'interventions' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Effectiveness by Channel</p>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={interventionChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748B' }} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                    <Tooltip contentStyle={{ background: '#0D1117', border: '1px solid #1E293B', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="total" fill="#334155" name="Total Sent" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="successful" fill="#10B981" name="Successful" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Success Rate by Channel</p>
                <div className="space-y-4 mt-2">
                  {interventionChartData.map((item: any) => (
                    <div key={item.name}>
                      <div className="flex justify-between mb-1">
                        <span className="text-xs font-mono text-slate-400">{item.name}</span>
                        <span className="text-xs font-mono text-slate-300">{item.successful}/{item.total} ({item.rate}%)</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full transition-all duration-1000"
                          style={{
                            width: `${item.rate}%`,
                            backgroundColor: item.rate >= 70 ? '#10B981' : item.rate >= 40 ? '#F59E0B' : '#F43F5E'
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* PROMISES TAB */}
        {activeTab === 'promises' && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Promise-to-Pay Tracker</p>
                <p className="text-sm text-slate-300">Customers who are likely to pay — tracked for follow-up</p>
              </div>
              <div className="flex gap-4 text-right">
                <div>
                  <p className="text-xs text-slate-500">Total</p>
                  <p className="text-2xl font-mono font-bold text-amber-400">{promiseTracker.total || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Pending</p>
                  <p className="text-2xl font-mono font-bold text-slate-300">{promiseTracker.pending || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <p className="text-xs font-mono text-slate-400 mb-2">How it works</p>
              <div className="space-y-2 text-xs text-slate-500">
                <p>→ When the LLM classifies a payment as <span className="text-amber-400 font-mono">promise_to_pay_likely: true</span>, it's tracked here</p>
                <p>→ A 24-hour follow-up window is set automatically</p>
                <p>→ If payment is completed within the window, promise is marked kept</p>
                <p>→ If not, it escalates to human review</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="bg-slate-800/30 rounded-lg p-4 text-center border border-slate-800">
                <p className="text-2xl font-mono font-bold text-amber-400">{promiseTracker.total || 0}</p>
                <p className="text-xs text-slate-500 mt-1">Promises Made</p>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-4 text-center border border-slate-800">
                <p className="text-2xl font-mono font-bold text-emerald-400">0</p>
                <p className="text-xs text-slate-500 mt-1">Promises Kept</p>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-4 text-center border border-slate-800">
                <p className="text-2xl font-mono font-bold text-rose-400">{promiseTracker.pending || 0}</p>
                <p className="text-xs text-slate-500 mt-1">Pending Follow-up</p>
              </div>
            </div>
          </div>
        )}

        {/* PAYMENTS TAB */}
        {activeTab === 'payments' && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
                {payments.length} payment records
              </p>
              <div className="flex gap-2">
                <select
                  className="text-xs font-mono bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1.5"
                  value={scenarioFilter}
                  onChange={(e) => setScenarioFilter(e.target.value)}
                >
                  <option value="">All scenarios</option>
                  <option value="payment_failure">Payment Failures</option>
                  <option value="checkout_abandonment">Cart Abandonments</option>
                  <option value="subscription_failure">Subscriptions</option>
                </select>
                <select
                  className="text-xs font-mono bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1.5"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="recovered">Recovered</option>
                  <option value="failed_recovery">Failed</option>
                  <option value="skipped">Skipped</option>
                  <option value="pending">Pending</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    {['ID', 'Amount', 'Scenario', 'Status', 'Failure', 'Customer', 'Audit'].map(h => (
                      <th key={h} className="text-left pb-3 text-xs font-mono text-slate-500 uppercase tracking-wider pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {payments.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-800/30 transition-colors group">
                      <td className="py-3 pr-4 font-mono text-xs text-slate-500">{p.id.slice(0, 14)}…</td>
                      <td className="py-3 pr-4 font-mono text-sm font-semibold text-slate-200">₹{(p.amount / 100).toFixed(0)}</td>
                      <td className="py-3 pr-4"><ScenarioBadge type={p.scenario_type || 'payment_failure'} /></td>
                      <td className="py-3 pr-4"><Badge status={p.status} /></td>
                      <td className="py-3 pr-4 text-xs text-slate-500 max-w-[140px] truncate">{p.failure_code}</td>
                      <td className="py-3 pr-4 text-xs text-slate-500 max-w-[130px] truncate">{p.customer_email}</td>
                      <td className="py-3">
                        <button
                          onClick={() => handleSelectPayment(p.id)}
                          className="text-xs font-mono text-blue-500 hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-all"
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="text-center py-4 border-t border-slate-800">
          <p className="text-xs text-slate-600 font-mono">
            PaybackAI — Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery —{' '}
            <a href="https://github.com/princemittalr/paybackai" className="text-blue-600 hover:text-blue-400">GitHub</a>
          </p>
        </div>

      </main>

      <AuditDrawer
        paymentId={selectedPayment}
        data={auditData}
        onClose={() => { setSelectedPayment(null); setAuditData(null); }}
      />
    </div>
  );
}