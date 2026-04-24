import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '../test-utils';
import SignInPage from '../../pages/SignInPage';

// ── Mock contexts/AuthContext ─────────────────────────────────────────────────
const mockLogin = vi.fn();
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin, isLoading: false }),
}));

// ── Mock react-router-dom navigate ───────────────────────────────────────────
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

describe('SignInPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email and password fields', () => {
    renderWithRouter(<SignInPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i, { selector: 'input' })).toBeInTheDocument();
  });

  it('renders a Sign In submit button', () => {
    renderWithRouter(<SignInPage />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows validation error when fields are empty', async () => {
    renderWithRouter(<SignInPage />);
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/fill in all fields/i);
  });

  it('calls login with email and password on valid submit', async () => {
    mockLogin.mockResolvedValue({ id: '1', email: 'test@example.com' });
    const user = userEvent.setup();
    renderWithRouter(<SignInPage />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i, { selector: 'input' }), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
  });

  it('navigates to /dashboard after successful login', async () => {
    mockLogin.mockResolvedValue({ id: '1' });
    const user = userEvent.setup();
    renderWithRouter(<SignInPage />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i, { selector: 'input' }), 'secret123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });

  it('shows an error message when login fails', async () => {
    const apiError = { response: { data: { detail: 'Incorrect email or password.' } } };
    mockLogin.mockRejectedValue(apiError);
    const user = userEvent.setup();
    renderWithRouter(<SignInPage />);

    await user.type(screen.getByLabelText(/email/i), 'wrong@example.com');
    await user.type(screen.getByLabelText(/password/i, { selector: 'input' }), 'wrongpass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect email or password/i);
  });

  it('renders a link to the sign-up page', () => {
    renderWithRouter(<SignInPage />);
    expect(screen.getByRole('link', { name: /create one/i })).toBeInTheDocument();
  });
});
