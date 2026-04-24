import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, logout as apiLogout } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('elan_user')); } catch { return null; }
  });
  const [isLoading, setIsLoading] = useState(false);

  const isAuthenticated = !!user && !!localStorage.getItem('elan_token');

  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    try {
      const data = await apiLogin(email, password);
      localStorage.setItem('elan_token', data.access_token);
      const u = data.user || { email };
      localStorage.setItem('elan_user', JSON.stringify(u));
      setUser(u);
      return u;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signup = useCallback(async (name, email, password) => {
    setIsLoading(true);
    try {
      const data = await apiRegister(name, email, password);
      localStorage.setItem('elan_token', data.access_token);
      const u = data.user || { name, email };
      localStorage.setItem('elan_user', JSON.stringify(u));
      setUser(u);
      return u;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
