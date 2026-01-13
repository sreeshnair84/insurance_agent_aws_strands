import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('password', password);

            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: params,
            });

            if (!res.ok) throw new Error('Login failed');
            const data = await res.json();
            login(data.access_token, { username: data.username, role: data.role });

            if (data.role === 'USER') navigate('/submit');
            else navigate('/dashboard');
        } catch (err) {
            setError('Invalid credentials');
        }
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            background: 'var(--bg-app)'
        }}>
            <form onSubmit={handleSubmit} className="glass" style={{
                padding: '2.5rem',
                borderRadius: '1rem',
                width: '100%',
                maxWidth: '400px',
                background: 'white' // Fallback/Base
            }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <div style={{
                        width: '48px', height: '48px',
                        background: 'var(--primary)',
                        borderRadius: '12px',
                        margin: '0 auto 1rem',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'white', fontSize: '24px',
                        boxShadow: '0 4px 6px rgba(37, 99, 235, 0.3)'
                    }}>🛡️</div>
                    <h2 style={{ margin: 0, color: 'var(--text-main)', fontSize: '1.5rem', fontWeight: 700 }}>Welcome Back</h2>
                    <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Sign in to access your claims</p>
                </div>

                {error && (
                    <div style={{
                        background: 'var(--status-error-bg)',
                        color: 'var(--status-error-text)',
                        padding: '0.75rem',
                        borderRadius: '0.5rem',
                        marginBottom: '1.5rem',
                        fontSize: '0.9rem',
                        display: 'flex', alignItems: 'center', gap: '0.5rem'
                    }}>
                        <span>⚠️</span> {error}
                    </div>
                )}

                <div style={{ marginBottom: '1.25rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-main)' }}>Username</label>
                    <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        className="input-field"
                        placeholder="e.g. user"
                    />
                </div>
                <div style={{ marginBottom: '2rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-main)' }}>Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        className="input-field"
                        placeholder="••••••••"
                    />
                </div>
                <button type="submit" className="btn-primary" style={{ width: '100%' }}>Sign In</button>
            </form>
        </div>
    );
}
