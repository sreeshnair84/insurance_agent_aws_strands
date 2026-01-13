import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ClaimSubmit() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        policy_number: '',
        claim_type: 'HEALTH',
        claim_amount: '',
        description: '',
        incident_date: ''
    });
    const [loading, setLoading] = useState(false);
    const [submitResult, setSubmitResult] = useState<any>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setSubmitResult(null);

        try {
            // 1. Create Claim
            const createRes = await fetch('/api/v1/claims/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    ...formData,
                    claim_amount: parseFloat(formData.claim_amount)
                })
            });

            if (!createRes.ok) {
                throw new Error('Failed to create claim');
            }

            const claim = await createRes.json();

            // 2. Submit for Validation
            const submitRes = await fetch(`/api/v1/claims/${claim.id}/submit`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });

            if (!submitRes.ok) {
                throw new Error('Failed to submit claim');
            }

            const result = await submitRes.json();
            setSubmitResult(result);

            // Reset form
            setFormData({
                policy_number: '',
                claim_type: 'HEALTH',
                claim_amount: '',
                description: '',
                incident_date: ''
            });

        } catch (err) {
            console.error(err);
            alert('Error submitting claim: ' + (err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <h1>New Claim</h1>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <button
                        onClick={() => navigate('/chat')}
                        style={{
                            padding: '0.5rem 1rem',
                            background: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            cursor: 'pointer'
                        }}
                    >
                        💬 Chat with Agent
                    </button>
                    <span>Welcome, {user?.username}</span>
                    <button onClick={logout} className="btn-primary" style={{ padding: '0.5rem 1rem' }}>Logout</button>
                </div>
            </header>

            {/* Success/Status Message */}
            {submitResult && (
                <div className="glass" style={{
                    padding: '1.5rem',
                    borderRadius: '1rem',
                    marginBottom: '2rem',
                    background: submitResult.status === 'completed' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                    borderLeft: `4px solid ${submitResult.status === 'completed' ? '#22c55e' : '#3b82f6'}`
                }}>
                    <h3 style={{ marginTop: 0, color: submitResult.status === 'completed' ? '#166534' : '#1e40af' }}>
                        {submitResult.status === 'completed' ? '✓ Claim Approved!' : '⏳ Claim Submitted for Review'}
                    </h3>

                    {submitResult.status === 'awaiting_approval' && (
                        <div>
                            <p style={{ margin: '0.5rem 0' }}>
                                <strong>Status:</strong> Pending Approver Review
                            </p>
                            <p style={{ margin: '0.5rem 0' }}>
                                <strong>Risk Level:</strong> <span style={{
                                    padding: '0.25rem 0.5rem',
                                    borderRadius: '0.5rem',
                                    background: submitResult.risk_level === 'HIGH' ? '#fee2e2' : submitResult.risk_level === 'MEDIUM' ? '#fef3c7' : '#dcfce7',
                                    color: submitResult.risk_level === 'HIGH' ? '#991b1b' : submitResult.risk_level === 'MEDIUM' ? '#92400e' : '#166534',
                                    fontSize: '0.85rem',
                                    fontWeight: 'bold'
                                }}>{submitResult.risk_level}</span>
                            </p>
                            {submitResult.summary && (
                                <div style={{
                                    marginTop: '1rem',
                                    padding: '1rem',
                                    background: 'rgba(255,255,255,0.5)',
                                    borderRadius: '0.5rem'
                                }}>
                                    <strong>AI Agent Analysis:</strong>
                                    <p style={{ margin: '0.5rem 0 0 0' }}>{submitResult.summary}</p>
                                </div>
                            )}
                            <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#666' }}>
                                An approver will review your claim shortly. You will be notified of the decision.
                            </p>
                        </div>
                    )}

                    {submitResult.status === 'completed' && (
                        <div>
                            <p style={{ margin: '0.5rem 0' }}>
                                Your claim has been automatically approved by the AI agent as it meets all criteria for low-risk claims.
                            </p>
                            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', color: '#666' }}>
                                {submitResult.message}
                            </p>
                        </div>
                    )}
                </div>
            )}

            <form onSubmit={handleSubmit} className="glass" style={{ padding: '2rem', borderRadius: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Policy Number</label>
                        <input type="text" className="input-field" required
                            value={formData.policy_number}
                            onChange={e => setFormData({ ...formData, policy_number: e.target.value })}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Type</label>
                        <select className="input-field" required
                            value={formData.claim_type}
                            onChange={e => setFormData({ ...formData, claim_type: e.target.value })}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                        >
                            <option value="HEALTH">Health</option>
                            <option value="AUTO">Auto</option>
                            <option value="PROPERTY">Property</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Amount ($)</label>
                        <input type="number" className="input-field" required
                            value={formData.claim_amount}
                            onChange={e => setFormData({ ...formData, claim_amount: e.target.value })}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Incident Date</label>
                        <input type="datetime-local" className="input-field" required
                            value={formData.incident_date}
                            onChange={e => setFormData({ ...formData, incident_date: e.target.value })}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                        />
                    </div>
                    <div style={{ gridColumn: 'span 2' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Description</label>
                        <textarea className="input-field" rows={4} required
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                        />
                    </div>
                </div>
                <div style={{ marginTop: '2rem', textAlign: 'right' }}>
                    <button disabled={loading} className="btn-primary" style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}>
                        {loading ? 'Processing...' : 'Submit Claim'}
                    </button>
                </div>
            </form>
        </div>
    );
}
