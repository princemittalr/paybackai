'use client';

interface AuditEvent {
  id: number;
  event_type: string;
  event_data: string;
  reasoning: string;
  timestamp: string;
}

interface RecoveryAction {
  id: number;
  action_type: string;
  action_reason: string;
  decision_explanation: string;
  executed_at: string;
  outcome: string;
  outcome_detail: string;
}

interface Props {
  paymentId: string | null;
  auditTrail: AuditEvent[];
  recoveryActions: RecoveryAction[];
  onClose: () => void;
}

const eventColors: Record<string, string> = {
  PROCESSING_STARTED: 'bg-blue-500',
  CLASSIFIED: 'bg-purple-500',
  INTERVENTION_SELECTED: 'bg-yellow-500',
  EMAIL_SENT: 'bg-green-500',
  SMS_SENT: 'bg-green-500',
  WHATSAPP_SENT: 'bg-green-500',
  BLACKLISTED: 'bg-red-500',
  STOPPED_BY_RULES: 'bg-orange-500',
  PROCESSING_COMPLETE: 'bg-teal-500',
};

export default function AuditDrawer({ paymentId, auditTrail, recoveryActions, onClose }: Props) {
  if (!paymentId) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 z-50 flex justify-end">
      <div className="bg-white w-full max-w-xl h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Audit Trail</h2>
            <p className="text-xs text-gray-500 font-mono">{paymentId}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl font-light">×</button>
        </div>

        <div className="px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Event Timeline</h3>
          <div className="space-y-3">
            {auditTrail.map((event) => (
              <div key={event.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={`w-3 h-3 rounded-full mt-1 flex-shrink-0 ${eventColors[event.event_type] || 'bg-gray-400'}`} />
                  <div className="w-px flex-1 bg-gray-200 mt-1" />
                </div>
                <div className="pb-3 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-800">{event.event_type}</span>
                    <span className="text-xs text-gray-400">{new Date(event.timestamp).toLocaleTimeString()}</span>
                  </div>
                  {event.reasoning && (
                    <p className="text-xs text-gray-600 mt-1">{event.reasoning}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {recoveryActions.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-700 mt-6 mb-3">Recovery Actions</h3>
              <div className="space-y-3">
                {recoveryActions.map((action) => (
                  <div key={action.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-gray-800">{action.action_type}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        action.outcome?.includes('DISPATCHED') || action.outcome === 'SUCCESS'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}>{action.outcome}</span>
                    </div>
                    <p className="text-xs text-gray-600">{action.decision_explanation}</p>
                    {action.outcome_detail && (
                      <p className="text-xs text-gray-400 mt-1">{action.outcome_detail}</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}