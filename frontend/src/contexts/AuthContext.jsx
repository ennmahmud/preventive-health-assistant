import { createContext, useContext, useState, useCallback } from 'react';
import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  updateProfile as apiUpdateProfile,
  changePassword as apiChangePassword,
  deleteAccount as apiDeleteAccount,
} from '../api/auth';
import { clearLocal as clearAssessmentCache } from '../utils/assessmentHistory';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('elan_user')); } catch { return null; }
  });
  const [isLoading, setIsLoading] = useState(false);

  const isAuthenticated = !!user && !!localStorage.getItem('elan_token');

  const _persistUser = (u) => {
    setUser(u);
    localStorage.setItem('elan_user', JSON.stringify(u));
  };

  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    try {
      const data = await apiLogin(email, password);
      localStorage.setItem('elan_token', data.access_token);
      const u = data.user || { email };
      _persistUser(u);
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
      _persistUser(u);
      return u;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    // Wipe this user's cached assessment history so the next account
    // logging in on the same browser doesn't see leftover data.
    clearAssessmentCache(user?.id);
    apiLogout();
    setUser(null);
  }, [user?.id]);

  /**
   * Update profile fields (name, dob, gender, height, weight).
   * Syncs with the backend and updates the in-memory + localStorage user.
   */
  const updateProfile = useCallback(async (fields) => {
    const updatedUser = await apiUpdateProfile(fields);
    _persistUser(updatedUser);
    return updatedUser;
  }, []);

  /**
   * Change password — throws if current password is wrong (HTTP 400).
   */
  const changePassword = useCallback(async (currentPassword, newPassword) => {
    await apiChangePassword(currentPassword, newPassword);
  }, []);

  /**
   * Permanently delete the account. Clears local auth state on success.
   */
  const deleteAccount = useCallback(async (password) => {
    await apiDeleteAccount(password);
    clearAssessmentCache(user?.id);
    setUser(null);
  }, [user?.id]);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isLoading,
      login,
      signup,
      logout,
      updateProfile,
      changePassword,
      deleteAccount,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
