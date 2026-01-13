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
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
            <header style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '2rem',
                background: 'var(--bg-panel)',
                padding: '1rem 1.5rem',
                borderRadius: '1rem',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-sm)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ fontSize: '1.5rem' }}>📝</div>
                    <h1 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text-main)', fontWeight: 600 }}>New Claim</h1>
                </div>

                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <button
                        onClick={() => navigate('/chat')}
                        style={{
                            padding: '0.5rem 1rem',
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            fontSize: '0.9rem'
                        }}
                        className="btn-secondary"
                    >
                        <span>💬</span> Chat with Agent
                    </button>
                    <div style={{ height: '24px', width: '1px', background: 'var(--border-color)' }}></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '28px', height: '28px',
                            borderRadius: '50%',
                            background: 'var(--bg-input)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '0.8rem', color: 'var(--text-muted)'
                        }}>👤</div>
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500 }}>{user?.username}</span>
                    </div>
                    <button onClick={logout} className="btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>Logout</button>
                </div>
            </header>

            {/* Success/Status Message */}
            {submitResult && (
                <div style={{
                    padding: '1.5rem',
                    borderRadius: '1rem',
                    marginBottom: '2rem',
                    background: submitResult.status === 'completed' ? 'var(--status-success-bg)' : 'var(--status-warning-bg)',
                    border: `1px solid ${submitResult.status === 'completed' ? 'transparent' : 'transparent'}`,
                    color: submitResult.status === 'completed' ? 'var(--status-success-text)' : 'var(--status-warning-text)',
                    boxShadow: 'var(--shadow-sm)'
                }}>
                    <h3 style={{ marginTop: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {submitResult.status === 'completed' ? '✅ Claim Approved' : '⏳ Claim Submitted for Review'}
                    </h3>

                    {submitResult.status === 'awaiting_approval' && (
                        <div>
                            <p style={{ margin: '0.5rem 0 1rem', opacity: 0.9 }}>
                                Your claim has been submitted pending approver review.
                            </p>
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.9rem' }}>
                                <span style={{ fontWeight: 600 }}>Risk Level:</span>
                                <span style={{
                                    padding: '0.25rem 0.75rem',
                                    borderRadius: '2rem',
                                    background: 'rgba(255,255,255,0.8)',
                                    fontWeight: 'bold',
                                    fontSize: '0.8rem'
                                }}>{submitResult.risk_level}</span>
                            </div>

                            {submitResult.summary && (
                                <div style={{
                                    marginTop: '1rem',
                                    padding: '1rem',
                                    background: 'rgba(255,255,255,0.6)',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.9rem'
                                }}>
                                    <strong style={{ display: 'block', marginBottom: '0.25rem' }}>AI Analysis</strong>
                                    {submitResult.summary}
                                </div>
                            )}
                        </div>
                    )}

                    {submitResult.status === 'completed' && (
                        <div>
                            <p style={{ margin: '0.5rem 0', opacity: 0.9 }}>
                                {submitResult.message || "Your claim meets all criteria for instant approval."}
                            </p>
                        </div>
                    )}
                </div>
            )}

            <form onSubmit={handleSubmit} className="glass" style={{ padding: '2.5rem', borderRadius: '1rem', background: 'var(--bg-panel)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>Policy Number</label>
                        <input type="text" className="input-field" required
                            value={formData.policy_number}
                            onChange={e => setFormData({ ...formData, policy_number: e.target.value })}
                            placeholder="POL-XXXXX"
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>Type</label>
                        <select className="input-field" required
                            value={formData.claim_type}
                            onChange={e => setFormData({ ...formData, claim_type: e.target.value })}
                        >
                            <option value="HEALTH">Health - Medical & Dental</option>
                            <option value="AUTO">Auto - Collision & Liability</option>
                            <option value="PROPERTY">Property - Home & Assets</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>Amount ($)</label>
                        <input type="number" className="input-field" required
                            value={formData.claim_amount}
                            onChange={e => setFormData({ ...formData, claim_amount: e.target.value })}
                            placeholder="0.00"
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>Incident Date</label>
                        <input type="datetime-local" className="input-field" required
                            value={formData.incident_date}
                            onChange={e => setFormData({ ...formData, incident_date: e.target.value })}
                        />
                    </div>
                    <div style={{ gridColumn: 'span 2' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>Description</label>
                        <textarea className="input-field" rows={4} required
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            style={{ resize: 'vertical' }}
                            placeholder="Describe what happened..."
                        />
                    </div>
                </div>
                <div style={{ textAlign: 'right', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
                    <button disabled={loading} className="btn-primary" style={{
                        padding: '0.75rem 2rem',
                        fontSize: '0.95rem',
                        opacity: loading ? 0.7 : 1,
                        cursor: loading ? 'not-allowed' : 'pointer'
                    }}>
                        {loading ? 'Processing...' : 'Submit Claim'}
                    </button>
                </div>
            </form>
        </div>
    );
}
