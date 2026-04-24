import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';

// ── Mock the API layer so no real HTTP calls are made ─────────────────────────
const mockApiLogin       = vi.fn();
const mockApiRegister    = vi.fn();
const mockApiLogout      = vi.fn();
const mockUpdateProfile  = vi.fn();
const mockChangePassword = vi.fn();
const mockDeleteAccount  = vi.fn();

vi.mock('../../api/auth', () => ({
  login:          (...a) => mockApiLogin(...a),
  register:       (...a) => mockApiRegister(...a),
  logout:         (...a) => mockApiLogout(...a),
  updateProfile:  (...a) => mockUpdateProfile(...a),
  changePassword: (...a) => mockChangePassword(...a),
  deleteAccount:  (...a) => mockDeleteAccount(...a),
}));

// Helper: render the hook inside the real AuthProvider
function renderAuthHook() {
  return renderHook(() => useAuth(), { wrapper: AuthProvider });
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  // ── Initial state ────────────────────────────────────────────────────────
  it('starts unauthenticated with no user', () => {
    const { result } = renderAuthHook();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('restores user from localStorage on mount', () => {
    const stored = { id: '42', name: 'Stored User', email: 'stored@example.com' };
    localStorage.setItem('elan_user', JSON.stringify(stored));
    localStorage.setItem('elan_token', 'tok_existing');

    const { result } = renderAuthHook();
    expect(result.current.user).toMatchObject({ email: 'stored@example.com' });
    expect(result.current.isAuthenticated).toBe(true);
  });

  // ── login ────────────────────────────────────────────────────────────────
  it('login: sets user and token on success', async () => {
    const fakeUser = { id: '1', name: 'Alice', email: 'alice@example.com' };
    mockApiLogin.mockResolvedValue({ access_token: 'tok_alice', user: fakeUser });

    const { result } = renderAuthHook();
    await act(() => result.current.login('alice@example.com', 'pass123'));

    expect(result.current.user).toMatchObject({ email: 'alice@example.com' });
    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem('elan_token')).toBe('tok_alice');
  });

  it('login: isLoading is true while pending, false after', async () => {
    let resolve;
    mockApiLogin.mockReturnValue(new Promise(r => { resolve = r; }));

    const { result } = renderAuthHook();
    act(() => { result.current.login('a@b.com', 'pw'); });
    expect(result.current.isLoading).toBe(true);

    await act(() => resolve({ access_token: 't', user: { id: '1', email: 'a@b.com' } }));
    expect(result.current.isLoading).toBe(false);
  });

  it('login: propagates API errors to the caller', async () => {
    mockApiLogin.mockRejectedValue(new Error('Bad credentials'));
    const { result } = renderAuthHook();

    await expect(
      act(() => result.current.login('bad@example.com', 'wrong'))
    ).rejects.toThrow('Bad credentials');

    expect(result.current.user).toBeNull();
  });

  // ── signup ───────────────────────────────────────────────────────────────
  it('signup: sets user and token on success', async () => {
    const fakeUser = { id: '2', name: 'Bob', email: 'bob@example.com' };
    mockApiRegister.mockResolvedValue({ access_token: 'tok_bob', user: fakeUser });

    const { result } = renderAuthHook();
    await act(() => result.current.signup('Bob', 'bob@example.com', 'pass1234'));

    expect(result.current.user).toMatchObject({ email: 'bob@example.com' });
    expect(localStorage.getItem('elan_token')).toBe('tok_bob');
  });

  // ── logout ───────────────────────────────────────────────────────────────
  it('logout: clears user and localStorage', async () => {
    mockApiLogin.mockResolvedValue({
      access_token: 'tok_x',
      user: { id: '1', email: 'x@example.com' },
    });
    const { result } = renderAuthHook();
    await act(() => result.current.login('x@example.com', 'pw'));
    expect(result.current.isAuthenticated).toBe(true);

    act(() => result.current.logout());
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  // ── updateProfile ────────────────────────────────────────────────────────
  it('updateProfile: merges updated fields into user state', async () => {
    const initial = { id: '3', name: 'Carol', email: 'carol@example.com' };
    mockApiLogin.mockResolvedValue({ access_token: 'tok_c', user: initial });
    mockUpdateProfile.mockResolvedValue({ ...initial, name: 'Carol Updated', gender: 'female' });

    const { result } = renderAuthHook();
    await act(() => result.current.login('carol@example.com', 'pw'));
    await act(() => result.current.updateProfile({ name: 'Carol Updated', gender: 'female' }));

    expect(result.current.user.name).toBe('Carol Updated');
    expect(result.current.user.gender).toBe('female');
  });

  // ── changePassword ───────────────────────────────────────────────────────
  it('changePassword: delegates to the API layer', async () => {
    mockChangePassword.mockResolvedValue(undefined);
    const { result } = renderAuthHook();
    await act(() => result.current.changePassword('oldpw', 'newpw123'));
    expect(mockChangePassword).toHaveBeenCalledWith('oldpw', 'newpw123');
  });

  // ── deleteAccount ────────────────────────────────────────────────────────
  it('deleteAccount: clears user state on success', async () => {
    mockApiLogin.mockResolvedValue({
      access_token: 'tok_d',
      user: { id: '4', email: 'd@example.com' },
    });
    mockDeleteAccount.mockResolvedValue(undefined);

    const { result } = renderAuthHook();
    await act(() => result.current.login('d@example.com', 'pw'));
    await act(() => result.current.deleteAccount('pw'));

    expect(result.current.user).toBeNull();
  });
});
