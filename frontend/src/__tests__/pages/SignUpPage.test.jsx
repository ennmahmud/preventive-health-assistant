import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '../test-utils';
import SignUpPage from '../../pages/SignUpPage';

// ── Mock contexts/AuthContext ─────────────────────────────────────────────────
const mockSignup = vi.fn();
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ signup: mockSignup, isLoading: false }),
}));

// ── Mock navigate ─────────────────────────────────────────────────────────────
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

describe('SignUpPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders all four fields', () => {
    renderWithRouter(<SignUpPage />);
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    const pwdFields = screen.getAllByLabelText(/password/i, { selector: 'input' });
    expect(pwdFields.length).toBeGreaterThanOrEqual(2);
  });

  it('shows error when required fields are missing', async () => {
    renderWithRouter(<SignUpPage />);
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/fill in all fields/i);
  });

  it('shows error when password is shorter than 8 characters', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), 'Alice');
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    const [pwdField] = screen.getAllByLabelText(/password/i, { selector: 'input' });
    await user.type(pwdField, 'short');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/at least 8 characters/i);
  });

  it('shows error when passwords do not match', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), 'Alice');
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    const [pwdField, confirmField] = screen.getAllByLabelText(/password/i, { selector: 'input' });
    await user.type(pwdField, 'password123');
    await user.type(confirmField, 'different99');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/do not match/i);
  });

  it('calls signup with name, email, and password on valid submit', async () => {
    mockSignup.mockResolvedValue({ id: '1' });
    const user = userEvent.setup();
    renderWithRouter(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), 'Alice');
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    const [pwdField, confirmField] = screen.getAllByLabelText(/password/i, { selector: 'input' });
    await user.type(pwdField, 'securepass');
    await user.type(confirmField, 'securepass');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(mockSignup).toHaveBeenCalledWith('Alice', 'alice@example.com', 'securepass');
  });

  it('navigates to /dashboard after successful signup', async () => {
    mockSignup.mockResolvedValue({ id: '1' });
    const user = userEvent.setup();
    renderWithRouter(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), 'Bob');
    await user.type(screen.getByLabelText(/email/i), 'bob@example.com');
    const [pwdField, confirmField] = screen.getAllByLabelText(/password/i, { selector: 'input' });
    await user.type(pwdField, 'password99');
    await user.type(confirmField, 'password99');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });

  it('shows API error on registration failure', async () => {
    mockSignup.mockRejectedValue({
      response: { data: { detail: 'An account with this email already exists.' } },
    });
    const user = userEvent.setup();
    renderWithRouter(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), 'Bob');
    await user.type(screen.getByLabelText(/email/i), 'dup@example.com');
    const [pwdField, confirmField] = screen.getAllByLabelText(/password/i, { selector: 'input' });
    await user.type(pwdField, 'password99');
    await user.type(confirmField, 'password99');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i);
  });
});
