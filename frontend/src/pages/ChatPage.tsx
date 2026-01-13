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

    const fetchClaims = async () => {
        try {
            const res = await fetch('/api/v1/claims/', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (res.ok) {
                const data = await res.json();
                setClaims(data);
                // Don't auto-select claim, default to General Chat if none selected
                // if (!selectedClaimId && data.length > 0) {
                //    setSelectedClaimId(data[0].id);
                // }
            }
        } catch (e) {
            console.error('Error fetching claims:', e);
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
                // Filter client-side just in case, though backend should handle it
                // If selectedClaimId is null, we only want messages where claim_id is null
                const filteredMessages = data.filter((m: Message) =>
                    selectedClaimId ? m.claim_id === selectedClaimId : m.claim_id === null
                );
                setMessages(filteredMessages);
            }
        } catch (e) {
            console.error('Error fetching messages:', e);
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
            } else {
                alert('Failed to send message');
                setInputMessage(messageContent); // Restore message on error
            }
        } catch (e) {
            console.error('Error sending message:', e);
            alert('Error sending message');
            setInputMessage(messageContent); // Restore message on error
        } finally {
            setSending(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const selectedClaim = claims.find(c => c.id === selectedClaimId);

    return (
        <div style={{ display: 'flex', height: '100vh', flexDirection: 'column' }}>
            {/* Header */}
            <header style={{
                padding: '1rem 2rem',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(255, 255, 255, 0.9)',
                backdropFilter: 'blur(10px)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h1 style={{ margin: 0, fontSize: '1.5rem' }}>💬 Chat with Agent</h1>
                    {selectedClaim ? (
                        <span style={{
                            padding: '0.25rem 0.75rem',
                            background: '#dbeafe',
                            color: '#1e40af',
                            borderRadius: '1rem',
                            fontSize: '0.875rem',
                            fontWeight: '500'
                        }}>
                            {selectedClaim.policy_number}
                        </span>
                    ) : (
                        <span style={{
                            padding: '0.25rem 0.75rem',
                            background: '#f3f4f6',
                            color: '#4b5563',
                            borderRadius: '1rem',
                            fontSize: '0.875rem',
                            fontWeight: '500'
                        }}>
                            General Inquiry & Claim Creation
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <button
                        onClick={() => navigate('/submit')}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'white',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.5rem',
                            cursor: 'pointer'
                        }}
                    >
                        ← Back to Claims
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
                                            fetchClaims(); // Refresh claims in case that list is stale? Actually unrelated.
                                        }
                                    } catch (e) {
                                        console.error("Failed to clear chat", e);
                                    }
                                }
                            }}
                            style={{
                                padding: '0.5rem 1rem',
                                background: '#fee2e2',
                                color: '#991b1b',
                                border: '1px solid #f87171',
                                borderRadius: '0.5rem',
                                cursor: 'pointer'
                            }}
                        >
                            Clear Chat
                        </button>
                    )}
                    <span>{user?.username}</span>
                    <button onClick={logout} className="btn-primary" style={{ padding: '0.5rem 1rem' }}>
                        Logout
                    </button>
                </div>
            </header>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* Sidebar - Claim Selector */}
                <div style={{
                    width: '300px',
                    borderRight: '1px solid #e5e7eb',
                    background: '#f9fafb',
                    padding: '1rem',
                    overflowY: 'auto'
                }}>
                    <div
                        onClick={() => setSelectedClaimId(null)}
                        style={{
                            padding: '0.75rem',
                            borderRadius: '0.5rem',
                            cursor: 'pointer',
                            background: selectedClaimId === null ? '#3b82f6' : 'white',
                            color: selectedClaimId === null ? 'white' : 'black',
                            border: '1px solid',
                            borderColor: selectedClaimId === null ? '#3b82f6' : '#e5e7eb',
                            marginBottom: '1rem',
                            fontWeight: 'bold'
                        }}
                    >
                        General Chat
                    </div>

                    <h3 style={{ marginTop: 0, fontSize: '1rem', marginBottom: '1rem' }}>Your Claims</h3>
                    {claims.length === 0 ? (
                        <p style={{ color: '#666', fontSize: '0.875rem' }}>No claims found</p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {claims.map(claim => (
                                <div
                                    key={claim.id}
                                    onClick={() => setSelectedClaimId(claim.id)}
                                    style={{
                                        padding: '0.75rem',
                                        borderRadius: '0.5rem',
                                        cursor: 'pointer',
                                        background: selectedClaimId === claim.id ? '#3b82f6' : 'white',
                                        color: selectedClaimId === claim.id ? 'white' : 'black',
                                        border: '1px solid',
                                        borderColor: selectedClaimId === claim.id ? '#3b82f6' : '#e5e7eb',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    <div style={{ fontWeight: '500', fontSize: '0.875rem' }}>
                                        {claim.policy_number}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '0.25rem' }}>
                                        {claim.claim_type} • {claim.status.replace('_', ' ')}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Chat Area */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {/* Messages */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '2rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1rem'
                    }}>
                        {messages.length === 0 ? (
                            <div style={{
                                textAlign: 'center',
                                color: '#9ca3af',
                                padding: '2rem'
                            }}>
                                <p>No messages yet. Start a conversation!</p>
                                {selectedClaimId === null ? (
                                    <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                        Try asking: "I want to create a new claim" or "List my claims"
                                    </p>
                                ) : (
                                    <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                        Try asking: "What is the status of my claim?"
                                    </p>
                                )}
                            </div>
                        ) : (
                            messages.map(msg => (
                                <div
                                    key={msg.id}
                                    style={{
                                        display: 'flex',
                                        justifyContent: msg.sender_type === 'USER' ? 'flex-end' : 'flex-start'
                                    }}
                                >
                                    <div style={{
                                        maxWidth: '70%',
                                        padding: '1rem',
                                        borderRadius: '1rem',
                                        background: msg.sender_type === 'USER'
                                            ? '#3b82f6'
                                            : 'rgba(255, 255, 255, 0.9)',
                                        color: msg.sender_type === 'USER' ? 'white' : 'black',
                                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                    }}>
                                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                                        {msg.a2ui && <A2UIRenderer components={msg.a2ui} />}
                                        <div style={{
                                            fontSize: '0.75rem',
                                            opacity: 0.7,
                                            marginTop: '0.5rem'
                                        }}>
                                            {new Date(msg.created_at).toLocaleTimeString()}
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                        {sending && (
                            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                                <div style={{
                                    padding: '1rem',
                                    borderRadius: '1rem',
                                    background: 'rgba(255, 255, 255, 0.9)',
                                    color: '#666',
                                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                                    display: 'flex',
                                    gap: '0.25rem',
                                    alignItems: 'center'
                                }}>
                                    <span style={{ animation: 'bounce 1s infinite', animationDelay: '0s' }}>●</span>
                                    <span style={{ animation: 'bounce 1s infinite', animationDelay: '0.2s' }}>●</span>
                                    <span style={{ animation: 'bounce 1s infinite', animationDelay: '0.4s' }}>●</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div style={{
                        borderTop: '1px solid #e5e7eb',
                        padding: '1rem 2rem',
                        background: 'white'
                    }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                            <textarea
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder={selectedClaimId === null
                                    ? "Ask general questions or create a claim..."
                                    : "Ask about this claim..."}
                                disabled={sending}
                                style={{
                                    flex: 1,
                                    padding: '0.75rem',
                                    borderRadius: '0.75rem',
                                    border: '1px solid #d1d5db',
                                    resize: 'none',
                                    minHeight: '60px',
                                    maxHeight: '150px',
                                    fontFamily: 'inherit',
                                    fontSize: '0.95rem'
                                }}
                                rows={2}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!inputMessage.trim() || sending}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: sending || !inputMessage.trim() ? '#9ca3af' : '#3b82f6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.75rem',
                                    cursor: sending || !inputMessage.trim() ? 'not-allowed' : 'pointer',
                                    fontWeight: '500',
                                    height: '60px'
                                }}
                            >
                                {sending ? 'Sending...' : 'Send'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
