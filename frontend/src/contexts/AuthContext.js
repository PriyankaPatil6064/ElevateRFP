// contexts/AuthContext.js
import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check if user is already logged in (from localStorage)
    const token = localStorage.getItem('elevateRFP_token');
    const userData = localStorage.getItem('elevateRFP_user');
    
    if (token && userData) {
      setIsAuthenticated(true);
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const login = (username, password) => {
    // Enhanced admin credentials with role-based access
    const adminUsers = {
      'admin': { password: 'elevate2024', role: 'administrator', name: 'System Administrator' },
      'manager': { password: 'manager2024', role: 'manager', name: 'RFP Manager' },
    };

    const user = adminUsers[username];
    if (user && user.password === password) {
      const token = `elevateRFP_${user.role}_token_${Date.now()}`;
      const userData = {
        username,
        role: user.role,
        name: user.name,
        loginTime: new Date().toISOString()
      };
      
      localStorage.setItem('elevateRFP_token', token);
      localStorage.setItem('elevateRFP_user', JSON.stringify(userData));
      
      setIsAuthenticated(true);
      setUser(userData);
      
      return { success: true, user: userData };
    }
    return { success: false, error: 'Invalid credentials. Please check your username and password.' };
  };

  const logout = () => {
    localStorage.removeItem('elevateRFP_token');
    localStorage.removeItem('elevateRFP_user');
    setIsAuthenticated(false);
    setUser(null);
  };

  const value = {
    isAuthenticated,
    user,
    login,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}