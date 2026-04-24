import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('pha_auth_user')); } catch { return null; }
  });

  const _persist = (u) => {
    setUser(u);
    if (u) localStorage.setItem('pha_auth_user', JSON.stringify(u));
    else    localStorage.removeItem('pha_auth_user');
  };

  const _getUsers = () => {
    try { return JSON.parse(localStorage.getItem('pha_users') || '[]'); } catch { return []; }
  };

  const _saveUsers = (list) => localStorage.setItem('pha_users', JSON.stringify(list));

  const login = useCallback((email, password) => {
    const users = _getUsers();
    const found = users.find(u => u.email === email && u.password === password);
    if (!found) throw new Error('Incorrect email or password.');
    const safe = strip(found);
    _persist(safe);
    return safe;
  }, []);

  const signup = useCallback((name, email, password) => {
    const users = _getUsers();
    if (users.find(u => u.email === email)) throw new Error('An account with this email already exists.');
    const id = crypto.randomUUID();
    const newUser = {
      id, name, email, password,
      createdAt: new Date().toISOString(),
      dob: '', gender: '', height: '', weight: '',
      avatarInitials: mkInitials(name),
    };
    _saveUsers([...users, newUser]);
    const safe = strip(newUser);
    _persist(safe);
    return safe;
  }, []);

  const logout = useCallback(() => _persist(null), []);

  const updateProfile = useCallback((updates) => {
    if (!user) return;
    const safe = { ...user, ...updates };
    if (updates.name) safe.avatarInitials = mkInitials(updates.name);
    _persist(safe);
    const users = _getUsers();
    const idx = users.findIndex(u => u.id === user.id);
    if (idx >= 0) { users[idx] = { ...users[idx], ...updates }; _saveUsers(users); }
  }, [user]);

  const changePassword = useCallback((currentPwd, newPwd) => {
    const users = _getUsers();
    const idx = users.findIndex(u => u.id === user?.id);
    if (idx < 0 || users[idx].password !== currentPwd) throw new Error('Current password is incorrect.');
    users[idx] = { ...users[idx], password: newPwd };
    _saveUsers(users);
  }, [user]);

  const deleteAccount = useCallback(() => {
    _saveUsers(_getUsers().filter(u => u.id !== user?.id));
    _persist(null);
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, logout, updateProfile, changePassword, deleteAccount }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

function strip({ password: _p, ...rest }) { return rest; }
function mkInitials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
}
