'use client';
import { useEffect, useState, useCallback, useRef } from 'react';
import {
  AreaChart, Area, PieChart, Pie, Cell, Tooltip,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Animated counter hook ──────────────────────────────
function useCountUp(target: number, duration = 1500) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (target === 0) return;
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(target * ease));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);
  return value;
}

// ── Status badge ───────────────────────────────────────
const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, string> = {
    recovered: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    failed_recovery: 'bg-rose-500/20 text-rose-400 border border-rose-500/30',
    skipped: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    pending: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${map[status] || map.pending}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

// ── Audit Drawer ───────────────────────────────────────
const AuditDrawer = ({ paymentId, data, onClose }: any) => {
  if (!paymentId) return null;
  const eventColors: Record<string, string> = {
    PROCESSING_STARTED: '#3B82F6',
    CLASSIFIED: '#8B5CF6',
    INTERVENTION_SELECTED: '#F59E0B',
    EMAIL_SENT: '#10B981',
    SMS_SENT: '#10B981',
    WHATSAPP_SENT: '#10B981',
    BLACKLISTED: '#F43F5E',
    STOPPED_BY_RULES: '#F97316',
    PROCESSING_COMPLETE: '#06B6D4',
  };
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end">
      <div className="bg-[#0D1117] border-l border-slate-800 w-full max-w-lg h-full overflow-y-auto">
        <div className="sticky top-0 bg-[#0D1117] border-b border-slate-800 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 font-mono mb-1">AUDIT TRAIL</p>
            <p className="text-sm font-mono text-slate-300 truncate">{paymentId}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors text-xl">✕</button>
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
                    {i < data.audit_trail.length - 1 && (
                      <div className="w-px flex-1 bg-slate-800 mt-1" />
                    )}
                  </div>
                  <div className="pb-5 flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-mono font-semibold text-slate-300">{event.event_type}</span>
                      <span className="text-xs text-slate-600 flex-shrink-0">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {event.reasoning && (
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">{event.reasoning}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          {data?.recovery_actions?.length > 0 && (
            <div>
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4">Recovery Actions</p>
              <div className="space-y-3">
                {data.recovery_actions.map((action: any) => (
                  <div key={action.id} className="bg-slate-900 rounded-lg p-4 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-slate-200">{action.action_type}</span>
                      <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                        action.outcome?.includes('DISPATCHED') || action.outcome === 'SUCCESS'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-slate-700 text-slate-400'
                      }`}>{action.outcome}</span>
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">{action.decision_explanation}</p>
                    {action.outcome_detail && (
                      <p className="text-xs text-slate-600 mt-1 font-mono">{action.outcome_detail}</p>
                    )}
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

// ── Main Dashboard ─────────────────────────────────────
export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [selectedPayment, setSelectedPayment] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<any>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, paymentsRes] = await Promise.all([
        fetch(`${API}/api/stats`),
        fetch(`${API}/api/payments?limit=60${statusFilter ? `&status=${statusFilter}` : ''}`)
      ]);
      const [statsData, paymentsData] = await Promise.all([statsRes.json(), paymentsRes.json()]);
      setStats(statsData);
      setPayments(paymentsData.payments || []);
      setLastUpdated(new Date());
    } catch (e) {
      console.error('Fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleSelectPayment = async (id: string) => {
    setSelectedPayment(id);
    const res = await fetch(`${API}/api/payments/${id}/audit`);
    const data = await res.json();
    setAuditData(data);
  };

  const summary = stats?.summary || {};
  const recentRuns = stats?.recent_runs || [];

  const recoveredCount = useCountUp(summary.recovered || 0);
  const amountRecovered = useCountUp(Math.floor(summary.total_amount_recovered_rupees || 0));
  const amountAtRisk = useCountUp(Math.floor(summary.total_amount_at_risk_rupees || 0));

  const pieData = [
    { name: 'Recovered', value: summary.recovered || 0, color: '#10B981' },
    { name: 'Failed', value: summary.failed_recovery || 0, color: '#F43F5E' },
    { name: 'Skipped', value: summary.skipped || 0, color: '#F59E0B' },
    { name: 'Pending', value: summary.pending || 0, color: '#475569' },
  ];

  const areaData = recentRuns
    .filter((r: any) => r.status === 'completed' && r.total_payments > 0)
    .reverse()
    .map((run: any, i: number) => ({
      name: `Run ${i + 1}`,
      recovered: run.recovered,
      failed: run.failed_recovery,
      amount: Math.floor(run.total_amount_recovered / 100),
    }));

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1E] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-slate-500 text-sm font-mono">Connecting to PaybackAI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0F1E] text-slate-100">

      {/* Header */}
      <header className="border-b border-slate-800/60 bg-[#0A0F1E]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-blue-500 rounded flex items-center justify-center">
              <span className="text-white text-xs font-bold">P</span>
            </div>
            <span className="font-semibold text-sm text-white">PaybackAI</span>
            <span className="text-slate-600 text-xs hidden sm:block">/ Recovery Dashboard</span>
          </div>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-xs text-slate-600 font-mono hidden sm:block">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-xs text-emerald-400 font-mono">LIVE</span>
            </div>
            <button
              onClick={fetchAll}
              className="text-xs text-slate-500 hover:text-white transition-colors font-mono border border-slate-800 hover:border-slate-600 px-3 py-1.5 rounded"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">

        {/* Hero metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              label: 'RECOVERY RATE',
              value: `${summary.recovery_rate || 0}%`,
              sub: `${recoveredCount} of ${summary.total_payments || 0} payments`,
              accent: 'text-emerald-400',
              border: 'border-emerald-500/20',
              bg: 'bg-emerald-500/5',
            },
            {
              label: 'AMOUNT RECOVERED',
              value: `₹${amountRecovered.toLocaleString('en-IN')}`,
              sub: 'Successfully recovered',
              accent: 'text-blue-400',
              border: 'border-blue-500/20',
              bg: 'bg-blue-500/5',
            },
            {
              label: 'TOTAL AT RISK',
              value: `₹${amountAtRisk.toLocaleString('en-IN')}`,
              sub: 'Failed payment value',
              accent: 'text-rose-400',
              border: 'border-rose-500/20',
              bg: 'bg-rose-500/5',
            },
            {
              label: 'FRAUD STOPPED',
              value: summary.skipped || 0,
              sub: 'Hard-stopped by rules',
              accent: 'text-amber-400',
              border: 'border-amber-500/20',
              bg: 'bg-amber-500/5',
            },
          ].map((card) => (
            <div key={card.label} className={`rounded-xl border ${card.border} ${card.bg} p-5`}>
              <p className="text-xs font-mono text-slate-500 tracking-widest mb-3">{card.label}</p>
              <p className={`text-2xl lg:text-3xl font-mono font-bold ${card.accent}`}>{card.value}</p>
              <p className="text-xs text-slate-600 mt-2">{card.sub}</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

          {/* Area chart — spans 3 cols */}
          <div className="lg:col-span-3 bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Recovery Trend</p>
            <p className="text-sm text-slate-300 mb-6">Payments recovered vs failed across batch runs</p>
            {areaData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={areaData}>
                  <defs>
                    <linearGradient id="gRecovered" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gFailed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#F43F5E" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#0D1117', border: '1px solid #1E293B', borderRadius: 8, fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="recovered" stroke="#10B981" fill="url(#gRecovered)" strokeWidth={2} name="Recovered" />
                  <Area type="monotone" dataKey="failed" stroke="#F43F5E" fill="url(#gFailed)" strokeWidth={2} name="Failed" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-slate-600 text-sm">No completed runs yet</div>
            )}
          </div>

          {/* Donut — spans 2 cols */}
          <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Breakdown</p>
            <p className="text-sm text-slate-300 mb-4">Payment outcome distribution</p>
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
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }} />
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
          <div className="space-y-2">
            {recentRuns.filter((r: any) => r.total_payments > 0).map((run: any) => {
              const rate = run.total_payments > 0 ? Math.round(run.recovered / run.total_payments * 100) : 0;
              return (
                <div key={run.run_id} className="flex items-center gap-4 p-3 rounded-lg bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-slate-400 truncate">{run.run_id}</p>
                    <p className="text-xs text-slate-600 mt-0.5">{new Date(run.started_at).toLocaleString()}</p>
                  </div>
                  <div className="flex items-center gap-6 text-right">
                    <div>
                      <p className="text-xs text-slate-500">Processed</p>
                      <p className="text-sm font-mono text-slate-200">{run.total_payments}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Recovered</p>
                      <p className="text-sm font-mono text-emerald-400">{run.recovered}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Rate</p>
                      <p className="text-sm font-mono text-blue-400">{rate}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Amount</p>
                      <p className="text-sm font-mono text-slate-200">₹{Math.floor(run.total_amount_recovered / 100).toLocaleString('en-IN')}</p>
                    </div>
                    <span className={`text-xs font-mono px-2 py-1 rounded ${run.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                      {run.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Payments table */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">Payment Records</p>
              <p className="text-sm text-slate-300">{payments.length} payments — click any row to see full audit trail</p>
            </div>
            <select
              className="text-xs font-mono bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
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

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Payment ID', 'Amount', 'Status', 'Failure', 'Customer', 'Retries', 'Audit'].map(h => (
                    <th key={h} className="text-left pb-3 text-xs font-mono text-slate-500 uppercase tracking-wider pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {payments.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="py-3 pr-4 font-mono text-xs text-slate-500">{p.id.slice(0, 16)}…</td>
                    <td className="py-3 pr-4 font-mono text-sm font-semibold text-slate-200">₹{(p.amount / 100).toFixed(2)}</td>
                    <td className="py-3 pr-4"><StatusBadge status={p.status} /></td>
                    <td className="py-3 pr-4 text-xs text-slate-500 max-w-[160px] truncate">{p.failure_code}</td>
                    <td className="py-3 pr-4 text-xs text-slate-500 max-w-[140px] truncate">{p.customer_email}</td>
                    <td className="py-3 pr-4 text-xs font-mono text-center text-slate-400">{p.retry_count}</td>
                    <td className="py-3">
                      <button
                        onClick={() => handleSelectPayment(p.id)}
                        className="text-xs font-mono text-blue-500 hover:text-blue-400 transition-colors opacity-0 group-hover:opacity-100"
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

        {/* Footer */}
        <div className="text-center py-4 border-t border-slate-800">
          <p className="text-xs text-slate-600 font-mono">
            PaybackAI — Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery
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