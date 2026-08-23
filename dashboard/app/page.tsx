'use client';
import { useEffect, useState, useCallback } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import StatCard from './components/StatCard';
import PaymentsTable from './components/PaymentsTable';
import AuditDrawer from './components/AuditDrawer';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [selectedPayment, setSelectedPayment] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<any>({ audit_trail: [], recovery_actions: [] });
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    const res = await fetch(`${API}/api/stats`);
    const data = await res.json();
    setStats(data);
  }, []);

  const fetchPayments = useCallback(async () => {
    const params = statusFilter ? `?status=${statusFilter}&limit=60` : '?limit=60';
    const res = await fetch(`${API}/api/payments${params}`);
    const data = await res.json();
    setPayments(data.payments || []);
  }, [statusFilter]);

  useEffect(() => {
    Promise.all([fetchStats(), fetchPayments()]).finally(() => setLoading(false));
  }, [fetchStats, fetchPayments]);

  const handleSelectPayment = async (id: string) => {
    setSelectedPayment(id);
    const res = await fetch(`${API}/api/payments/${id}/audit`);
    const data = await res.json();
    setAuditData(data);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">⚡</div>
          <p className="text-gray-600 font-medium">Loading PaybackAI...</p>
        </div>
      </div>
    );
  }

  const summary = stats?.summary || {};
  const recentRuns = stats?.recent_runs || [];

  const pieData = [
    { name: 'Recovered', value: summary.recovered || 0, color: '#22c55e' },
    { name: 'Failed', value: summary.failed_recovery || 0, color: '#ef4444' },
    { name: 'Skipped', value: summary.skipped || 0, color: '#f59e0b' },
    { name: 'Pending', value: summary.pending || 0, color: '#94a3b8' },
  ];

  const barData = recentRuns.map((run: any) => ({
    name: run.run_id.slice(-6),
    recovered: run.recovered,
    failed: run.failed_recovery,
    skipped: run.skipped,
  }));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚡</span>
            <div>
              <h1 className="text-xl font-bold text-gray-900">PaybackAI</h1>
              <p className="text-xs text-gray-500">Autonomous Payment Recovery Agent</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-600">Live</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">

        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Recovery Rate"
            value={`${summary.recovery_rate || 0}%`}
            subtitle={`${summary.recovered} of ${summary.total_payments} payments`}
            color="green"
            icon="✅"
          />
          <StatCard
            title="Amount Recovered"
            value={`₹${(summary.total_amount_recovered_rupees || 0).toLocaleString('en-IN')}`}
            subtitle="Successfully recovered"
            color="blue"
            icon="💰"
          />
          <StatCard
            title="Amount at Risk"
            value={`₹${(summary.total_amount_at_risk_rupees || 0).toLocaleString('en-IN')}`}
            subtitle="Total failed payment value"
            color="red"
            icon="⚠️"
          />
          <StatCard
            title="Fraud Stopped"
            value={summary.skipped || 0}
            subtitle="Hard-stopped by rules"
            color="yellow"
            icon="🛡️"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Recovery Breakdown</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value">
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [value, name]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-3 mt-2 justify-center">
              {pieData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span className="text-xs text-gray-600">{entry.name} ({entry.value})</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Batch Run History</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="recovered" fill="#22c55e" radius={[4, 4, 0, 0]} name="Recovered" />
                <Bar dataKey="failed" fill="#ef4444" radius={[4, 4, 0, 0]} name="Failed" />
                <Bar dataKey="skipped" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Skipped" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Payments Table */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">All Payments</h2>
            <select
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-600"
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
          <PaymentsTable payments={payments} onSelectPayment={handleSelectPayment} />
        </div>

        {/* Recent Runs */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Recent Batch Runs</h2>
          <div className="space-y-3">
            {recentRuns.map((run: any) => (
              <div key={run.run_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <p className="text-xs font-mono text-gray-500">{run.run_id}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{new Date(run.started_at).toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-800">
                    {run.recovered}/{run.total_payments} recovered
                  </p>
                  <p className="text-xs text-gray-500">
                    ₹{(run.total_amount_recovered / 100).toLocaleString('en-IN')} recovered
                  </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                  run.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {run.status}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Audit Drawer */}
      <AuditDrawer
        paymentId={selectedPayment}
        auditTrail={auditData.audit_trail}
        recoveryActions={auditData.recovery_actions}
        onClose={() => setSelectedPayment(null)}
      />
    </div>
  );
}