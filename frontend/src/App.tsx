import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ClaimSubmit from './pages/ClaimSubmit';
import ChatPage from './pages/ChatPage';

const PrivateRoute = ({ children, roles }: { children: JSX.Element, roles?: string[] }) => {
    const { user, token } = useAuth();
    if (!token) return <Navigate to="/login" />;
    if (roles && user && !roles.includes(user.role)) return <Navigate to="/" />;
    return children;
};

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />

                {/* User Routes */}
                <Route path="/submit" element={
                    <PrivateRoute roles={['USER']}>
                        <ClaimSubmit />
                    </PrivateRoute>
                } />

                <Route path="/chat" element={
                    <PrivateRoute roles={['USER']}>
                        <ChatPage />
                    </PrivateRoute>
                } />

                {/* Approver Routes */}
                <Route path="/dashboard" element={
                    <PrivateRoute roles={['APPROVER', 'ADMIN']}>
                        <Dashboard />
                    </PrivateRoute>
                } />

                <Route path="/" element={<Navigate to="/login" />} />
            </Routes>
        </Router>
    );
}

export default App;
