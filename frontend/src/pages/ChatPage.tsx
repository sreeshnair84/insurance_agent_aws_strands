import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { A2UIRenderer } from '../components/A2UIRenderer';

interface Message {
    id: number;
    claim_id: number | null;
    sender_type: string;
    sender_id: number | null;
    content: string;
    a2ui: any[] | null;
    created_at: string;
}

interface Claim {
    id: number;
    policy_number: string;
    claim_type: string;
    status: string;
}

export default function ChatPage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const claimIdParam = searchParams.get('claim_id');

    const [claims, setClaims] = useState<Claim[]>([]);
    const [selectedClaimId, setSelectedClaimId] = useState<number | null>(
        claimIdParam ? parseInt(claimIdParam) : null
    );
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Fetch user's claims
    useEffect(() => {
        fetchClaims();
        // Poll for claims update (in case created via chat)
        const claimInterval = setInterval(fetchClaims, 5000);
        return () => clearInterval(claimInterval);
    }, []);

    // Fetch messages when claim is selected (or specifically for general chat)
    useEffect(() => {
        fetchMessages();
        // Poll for new messages every 3 seconds
        const interval = setInterval(fetchMessages, 3000);
        return () => clearInterval(interval);
    }, [selectedClaimId]);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleBackendError = (e: any) => {
        console.error("Backend Error:", e);
        // Check for network error (fetch failure) or potential 500s if response was available (but here we only catch exceptions)
        // 'TypeError: Failed to fetch' is typical for network down/CORS/Refused connection
        if (e instanceof TypeError || e.message?.toLowerCase().includes('fetch')) {
            console.log("Backend appears down, redirecting to login");
            logout();
            // Navigate handled by AuthContext usually clearing user, but explicit nav helps
            navigate('/login?error=connection_lost');
        }
    };

    const fetchClaims = async () => {
        try {
            const res = await fetch('/api/v1/claims/', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) {
                const data = await res.json();
                setClaims(data);
            } else if (res.status >= 500) {
                throw new Error("Server Error");
            }
        } catch (e) {
            handleBackendError(e);
        }
    };

    const fetchMessages = async () => {
        try {
            let url = '/api/v1/chat/messages';
            if (selectedClaimId) {
                url += `/${selectedClaimId}`;
            }

            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) {
                const data = await res.json();
                const filteredMessages = data.filter((m: Message) =>
                    selectedClaimId ? m.claim_id === selectedClaimId : m.claim_id === null
                );
                setMessages(filteredMessages);
            } else if (res.status >= 500) {
                throw new Error("Server Error");
            }
        } catch (e) {
            handleBackendError(e);
        } finally {
            setLoading(false);
        }
    };

    const sendMessage = async () => {
        if (!inputMessage.trim() || sending) return;

        setSending(true);
        const messageContent = inputMessage.trim();
        setInputMessage(''); // Clear input immediately

        try {
            const res = await fetch('/api/v1/chat/send', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    claim_id: selectedClaimId, // Can be null
                    content: messageContent
                })
            });

            if (res.ok) {
                const data = await res.json();
                setMessages(prev => [...prev, data.user_message, data.agent_message]);
                // Refresh claims if we are in general chat (might have created one)
                if (!selectedClaimId) fetchClaims();
            } else if (res.status >= 500) {
                throw new Error("Server Error");
            } else {
                alert('Failed to send message');
                setInputMessage(messageContent); // Restore message on error
            }
        } catch (e) {
            handleBackendError(e);
            alert('Error sending message - Service may be down');
            setInputMessage(messageContent); // Restore message
        } finally {
            setSending(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const selectedClaim = claims.find(c => c.id === selectedClaimId);

    return (
        <div style={{ display: 'flex', height: '100vh', flexDirection: 'column', background: 'var(--bg-app)' }}>
            {/* Header */}
            <header className="glass" style={{
                padding: '1rem 2rem',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                zIndex: 10,
                background: 'white'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        background: 'var(--primary-light)',
                        color: 'var(--primary)',
                        padding: '0.5rem',
                        borderRadius: '0.5rem',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                        <span style={{ fontSize: '1.2rem' }}>💎</span>
                    </div>
                    <div>
                        <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>Strands Agent</h1>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>AI-Powered Claims Assistant</span>
                    </div>

                    {selectedClaim ? (
                        <span style={{
                            marginLeft: '1rem',
                            padding: '0.25rem 0.75rem',
                            background: 'var(--primary-light)',
                            color: 'var(--primary)',
                            border: '1px solid var(--primary-subtle)',
                            borderRadius: '1rem',
                            fontSize: '0.75rem',
                            fontWeight: '600'
                        }}>
                            {selectedClaim.policy_number}
                        </span>
                    ) : (
                        <span style={{
                            marginLeft: '1rem',
                            padding: '0.25rem 0.75rem',
                            background: 'var(--bg-input)',
                            color: 'var(--text-muted)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '1rem',
                            fontSize: '0.75rem',
                        }}>
                            General Chat
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <button onClick={() => navigate('/submit')} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem' }}>
                        <span>←</span> Back
                    </button>
                    {selectedClaimId === null && (
                        <button
                            onClick={async () => {
                                if (confirm('Are you sure you want to clear the chat history?')) {
                                    try {
                                        const res = await fetch('/api/v1/chat/messages', {
                                            method: 'DELETE',
                                            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                                        });
                                        if (res.ok) {
                                            setMessages([]);
                                            fetchClaims();
                                        }
                                    } catch (e) {
                                        console.error("Failed to clear chat", e);
                                    }
                                }
                            }}
                            className="btn-danger"
                            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
                        >
                            Clear Chat
                        </button>
                    )}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--bg-input)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', color: 'var(--text-muted)', border: '1px solid var(--border-color)' }}>
                            {user?.username?.charAt(0).toUpperCase()}
                        </div>
                    </div>
                </div>
            </header>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* Sidebar - Claim Selector */}
                <div className="glass" style={{
                    width: '300px',
                    borderRight: '1px solid var(--border-color)',
                    borderLeft: 'none', borderTop: 'none', borderBottom: 'none',
                    padding: '1rem',
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    background: 'white'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                        <div style={{
                            width: '36px', height: '36px',
                            background: 'var(--primary)',
                            borderRadius: '8px',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'white', fontSize: '18px'
                        }}>🛡️</div>
                        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>Insurant</h1>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                        <button style={{
                            padding: '0.75rem 1rem',
                            background: 'var(--primary-light)',
                            color: 'var(--primary)',
                            border: '1px solid var(--primary-subtle)',
                            borderRadius: '0.5rem',
                            textAlign: 'left',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: '0.75rem'
                        }} onClick={() => setSelectedClaimId(null)}>
                            <span>➕</span> New Claim Chat
                        </button>

                        <div style={{ marginTop: '1.5rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Your Sessions
                        </div>

                        {claims.map(claim => (
                            <div
                                key={claim.id}
                                onClick={() => setSelectedClaimId(claim.id)}
                                style={{
                                    padding: '0.75rem',
                                    borderRadius: '0.5rem',
                                    background: selectedClaimId === claim.id ? 'var(--bg-input)' : 'transparent',
                                    cursor: 'pointer',
                                    border: selectedClaimId === claim.id ? '1px solid var(--border-color)' : '1px solid transparent',
                                    color: selectedClaimId === claim.id ? 'var(--text-main)' : 'var(--text-secondary)',
                                    fontSize: '0.9rem',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <div style={{ fontWeight: 500 }}>Claim #{claim.policy_number}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{claim.claim_type} • {claim.status}</div>
                            </div>
                        ))}
                    </div>

                    <div style={{
                        padding: '1rem',
                        background: 'var(--bg-app)',
                        borderRadius: '0.75rem',
                        display: 'flex', alignItems: 'center', gap: '0.75rem',
                        marginTop: 'auto',
                        border: '1px solid var(--border-color)'
                    }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--bg-input)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>👤</div>
                        <div style={{ flex: 1, overflow: 'hidden' }}>
                            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>{user?.username}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user?.role}</div>
                        </div>
                        <button onClick={logout} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                            🚪
                        </button>
                    </div>
                </div>

                {/* Main Chat Area */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '2rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1.5rem',
                        scrollBehavior: 'smooth',
                        background: 'var(--bg-app)'
                    }}>
                        {messages.length === 0 ? (
                            <div style={{
                                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                height: '100%', opacity: 0.6
                            }}>
                                <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>👋</div>
                                <h3 style={{ color: 'var(--text-main)', marginBottom: '0.5rem' }}>How can I help you today?</h3>
                                <p style={{ color: 'var(--text-muted)' }}>Ask about claims, policies, or create a new request.</p>
                            </div>
                        ) : (
                            messages.map((msg) => (
                                <div key={msg.id} style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: msg.sender_type === 'USER' ? 'flex-end' : 'flex-start',
                                    maxWidth: '100%'
                                }}>
                                    <div style={{
                                        maxWidth: '800px',
                                        width: '100%',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: msg.sender_type === 'USER' ? 'flex-end' : 'flex-start'
                                    }}>
                                        {/* Text Bubble */}
                                        {msg.content && (
                                            <div style={{
                                                padding: '1rem 1.25rem',
                                                borderRadius: '1rem',
                                                borderTopRightRadius: msg.sender_type === 'USER' ? '0.25rem' : '1rem',
                                                borderTopLeftRadius: msg.sender_type === 'AGENT' ? '0.25rem' : '1rem',
                                                background: msg.sender_type === 'USER' ? 'var(--primary)' : 'white',
                                                color: msg.sender_type === 'USER' ? 'white' : 'var(--text-main)',
                                                boxShadow: 'var(--shadow-sm)',
                                                border: msg.sender_type === 'AGENT' ? '1px solid var(--border-color)' : 'none',
                                                fontSize: '0.95rem',
                                                lineHeight: '1.5'
                                            }}>
                                                {msg.content}
                                            </div>
                                        )}

                                        {/* A2UI Components */}
                                        {msg.a2ui && (
                                            <div style={{ width: '100%', maxWidth: '600px', marginTop: '0.5rem' }}>
                                                <A2UIRenderer components={msg.a2ui} />
                                            </div>
                                        )}

                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem', padding: '0 0.5rem' }}>
                                            {msg.sender_type === 'AGENT' ? 'Insurant AI' : 'You'} • {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                        {sending && (
                            <div style={{
                                alignSelf: 'flex-start',
                                padding: '0.75rem 1.25rem',
                                background: 'white',
                                borderRadius: '1rem',
                                border: '1px solid var(--border-color)',
                                color: 'var(--text-muted)',
                                fontSize: '0.9rem',
                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                boxShadow: 'var(--shadow-sm)'
                            }}>
                                <span className="typing-dot"></span>
                                <span className="typing-dot"></span>
                                <span className="typing-dot"></span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="glass" style={{
                        padding: '1.5rem 2rem',
                        borderTop: '1px solid var(--border-color)',
                        display: 'flex', justifyContent: 'center',
                        background: 'white'
                    }}>
                        <div style={{ width: '100%', maxWidth: '900px', position: 'relative' }}>
                            <input
                                type="text"
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                                placeholder="Type your message..."
                                disabled={sending}
                                className="input-field"
                                style={{
                                    width: '100%',
                                    paddingRight: '3rem',
                                    height: '50px',
                                    borderRadius: '1.5rem',
                                    paddingLeft: '1.5rem',
                                    fontSize: '1rem',
                                    boxShadow: 'var(--shadow-sm)'
                                }}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!inputMessage.trim() || sending}
                                style={{
                                    position: 'absolute',
                                    right: '0.5rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    width: '36px',
                                    height: '36px',
                                    borderRadius: '50%',
                                    border: 'none',
                                    background: inputMessage.trim() ? 'var(--primary)' : 'var(--bg-input)',
                                    color: inputMessage.trim() ? 'white' : 'var(--text-muted)',
                                    cursor: inputMessage.trim() ? 'pointer' : 'default',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    transition: 'all 0.2s'
                                }}
                            >
                                ➤
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
