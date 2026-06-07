// pages/LoginPage.jsx
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Triangle, Loader2, Lock } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const { login }  = useAuth();
  const navigate   = useNavigate();
  const location   = useLocation();
  const from       = location.state?.from?.pathname || '/dashboard';

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }
    setLoading(true);
    setError('');
    const result = login(username, password);
    if (result.success) {
      navigate(from, { replace: true });
    } else {
      setError(result.error);
    }
    setLoading(false);
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Brand */}
        <div className="login-brand-row">
          <div className="brand-icon-wrap">
            <Triangle size={14} fill="currentColor" />
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
            Elevate<span style={{ color: 'var(--accent)' }}>RFP</span>
          </span>
        </div>

        <h2 className="login-title">Sign in</h2>
        <p className="login-subtitle">Access the RFP Automation Console</p>

        {error && (
          <div className="alert alert-error">
            <Lock size={13} style={{ flexShrink: 0 }} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              className="form-input"
              placeholder="Enter username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              placeholder="Enter password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full btn-lg"
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? (
              <><Loader2 size={15} className="spin" /> Signing in…</>
            ) : (
              <><Lock size={14} /> Sign In</>
            )}
          </button>
        </form>

        <hr className="login-divider" />

        {/* Demo creds */}
        <div className="demo-creds">
          <div className="demo-creds-title">Demo Credentials</div>
          <div className="demo-creds-row">
            <span>Administrator</span>
            <span><code>admin</code> / <code>elevate2024</code></span>
          </div>
          <div className="demo-creds-row">
            <span>Manager</span>
            <span><code>manager</code> / <code>manager2024</code></span>
          </div>
        </div>
      </div>
    </div>
  );
}