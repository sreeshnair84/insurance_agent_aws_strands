import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

interface Claim {
    id: number;
    policy_number: string;
    claim_type: string;
    claim_amount: number;
    status: string;
    fraud_risk_score: number;
    description: string;
    claim_metadata?: {
        interrupt_reason?: {
            risk_level?: string;
            summary?: string;
        };
    };
}

export default function Dashboard() {
    const { user, logout } = useAuth();
    const [claims, setClaims] = useState<Claim[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [showRequestInfoModal, setShowRequestInfoModal] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [requestedInfo, setRequestedInfo] = useState('');

    const fetchClaims = async () => {
        try {
            const res = await fetch('/api/v1/claims/', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) setClaims(await res.json());
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchClaims(); }, []);

    const handleApprove = async (id: number) => {
        if (!confirm('Are you sure you want to approve this claim?')) return;

        try {
            const res = await fetch(`/api/v1/claims/${id}/approve`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ reason: 'Approved after review' })
            });
            if (res.ok) {
                alert('Claim approved successfully');
                fetchClaims();
            } else {
                alert('Approval failed');
            }
        } catch (e) {
            console.error(e);
            alert('Error approving claim');
        }
    };

    const handleReject = async () => {
        if (!selectedClaim || !rejectReason.trim()) {
            alert('Please provide a reason for rejection');
            return;
        }

        try {
            const res = await fetch(`/api/v1/claims/${selectedClaim.id}/reject`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ reason: rejectReason })
            });
            if (res.ok) {
                alert('Claim rejected');
                setShowRejectModal(false);
                setRejectReason('');
                setSelectedClaim(null);
                fetchClaims();
            } else {
                alert('Rejection failed');
            }
        } catch (e) {
            console.error(e);
            alert('Error rejecting claim');
        }
    };

    const handleRequestInfo = async () => {
        if (!selectedClaim || !requestedInfo.trim()) {
            alert('Please specify what information is needed');
            return;
        }

        try {
            const res = await fetch(`/api/v1/claims/${selectedClaim.id}/request-info`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ requested_info: requestedInfo })
            });
            if (res.ok) {
                alert('Information request sent to user');
                setShowRequestInfoModal(false);
                setRequestedInfo('');
                setSelectedClaim(null);
                fetchClaims();
            } else {
                alert('Request failed');
            }
        } catch (e) {
            console.error(e);
            alert('Error requesting information');
        }
    };

    const getRiskBadge = (claim: Claim) => {
        const riskLevel = claim.claim_metadata?.interrupt_reason?.risk_level;
        if (!riskLevel) return null;

        const colors = {
            HIGH: { bg: '#fee2e2', color: '#991b1b' },
            MEDIUM: { bg: '#fef3c7', color: '#92400e' },
            LOW: { bg: '#dcfce7', color: '#166534' }
        };

        const style = colors[riskLevel as keyof typeof colors] || colors.MEDIUM;

        return (
            <span style={{
                padding: '0.25rem 0.5rem',
                borderRadius: '0.5rem',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                background: style.bg,
                color: style.color
            }}>
                {riskLevel} RISK
            </span>
        );
    };

    return (
        <div style={{ padding: '2rem' }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <h1>Approver Dashboard</h1>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <span>{user?.username} ({user?.role})</span>
                    <button onClick={logout} className="btn-primary" style={{ padding: '0.5rem 1rem' }}>Logout</button>
                </div>
            </header>

            {loading ? <p>Loading...</p> : (
                <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))' }}>
                    {claims.map(claim => (
                        <div key={claim.id} className="glass" style={{ padding: '1.5rem', borderRadius: '1rem', position: 'relative', overflow: 'hidden' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'center' }}>
                                <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{claim.policy_number}</span>
                                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                    {getRiskBadge(claim)}
                                    <span style={{
                                        padding: '0.25rem 0.5rem', borderRadius: '1rem', fontSize: '0.8rem',
                                        background: claim.status === 'APPROVED' ? '#dcfce7' : claim.status === 'REJECTED' ? '#fee2e2' : claim.status === 'PENDING_APPROVAL' ? '#dbeafe' : '#fef3c7',
                                        color: claim.status === 'APPROVED' ? '#166534' : claim.status === 'REJECTED' ? '#991b1b' : claim.status === 'PENDING_APPROVAL' ? '#1e40af' : '#92400e'
                                    }}>{claim.status.replace('_', ' ')}</span>
                                </div>
                            </div>

                            {/* Agent Summary */}
                            {claim.claim_metadata?.interrupt_reason?.summary && (
                                <div style={{
                                    background: 'rgba(59, 130, 246, 0.1)',
                                    padding: '0.75rem',
                                    borderRadius: '0.5rem',
                                    marginBottom: '1rem',
                                    borderLeft: '3px solid #3b82f6'
                                }}>
                                    <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#3b82f6', marginBottom: '0.25rem' }}>
                                        AI AGENT SUMMARY
                                    </div>
                                    <div style={{ fontSize: '0.9rem', color: '#1e3a8a' }}>
                                        {claim.claim_metadata.interrupt_reason.summary}
                                    </div>
                                </div>
                            )}

                            <p style={{ margin: '0 0 1rem 0', color: '#666' }}>{claim.description}</p>

                            <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '1rem' }}>
                                <div>Type: {claim.claim_type}</div>
                                <div>Amount: ${claim.claim_amount.toLocaleString()}</div>
                                <div>Fraud Risk Score: {claim.fraud_risk_score}</div>
                            </div>

                            {claim.status === 'PENDING_APPROVAL' && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                                    <button
                                        onClick={() => handleApprove(claim.id)}
                                        style={{ background: '#22c55e', color: 'white', border: 'none', padding: '0.5rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}
                                    >✓ Approve</button>
                                    <button
                                        onClick={() => { setSelectedClaim(claim); setShowRejectModal(true); }}
                                        style={{ background: '#ef4444', color: 'white', border: 'none', padding: '0.5rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}
                                    >✗ Reject</button>
                                    <button
                                        onClick={() => { setSelectedClaim(claim); setShowRequestInfoModal(true); }}
                                        style={{ background: '#f59e0b', color: 'white', border: 'none', padding: '0.5rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}
                                    >? More Info</button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Reject Modal */}
            {showRejectModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}>
                    <div className="glass" style={{ padding: '2rem', borderRadius: '1rem', maxWidth: '500px', width: '90%' }}>
                        <h2 style={{ marginTop: 0 }}>Reject Claim</h2>
                        <p>Policy: {selectedClaim?.policy_number}</p>
                        <textarea
                            placeholder="Reason for rejection (required)"
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            style={{ width: '100%', minHeight: '100px', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc', marginBottom: '1rem' }}
                        />
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                            <button onClick={() => { setShowRejectModal(false); setRejectReason(''); setSelectedClaim(null); }} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', border: '1px solid #ccc', background: 'white', cursor: 'pointer' }}>
                                Cancel
                            </button>
                            <button onClick={handleReject} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', background: '#ef4444', color: 'white', cursor: 'pointer' }}>
                                Reject Claim
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Request Info Modal */}
            {showRequestInfoModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}>
                    <div className="glass" style={{ padding: '2rem', borderRadius: '1rem', maxWidth: '500px', width: '90%' }}>
                        <h2 style={{ marginTop: 0 }}>Request Additional Information</h2>
                        <p>Policy: {selectedClaim?.policy_number}</p>
                        <textarea
                            placeholder="What information do you need from the user?"
                            value={requestedInfo}
                            onChange={(e) => setRequestedInfo(e.target.value)}
                            style={{ width: '100%', minHeight: '100px', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ccc', marginBottom: '1rem' }}
                        />
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                            <button onClick={() => { setShowRequestInfoModal(false); setRequestedInfo(''); setSelectedClaim(null); }} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', border: '1px solid #ccc', background: 'white', cursor: 'pointer' }}>
                                Cancel
                            </button>
                            <button onClick={handleRequestInfo} style={{ padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', background: '#f59e0b', color: 'white', cursor: 'pointer' }}>
                                Send Request
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
