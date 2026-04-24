/**
 * Custom render helpers that wrap components with the providers they need.
 *
 * Usage:
 *   import { renderWithRouter } from '../test-utils';
 *
 * For components that call useAuth(), vi.mock the contexts/AuthContext module
 * directly in the test file instead of wrapping here — the context object
 * itself is not a named export so mocking the module is cleaner.
 */
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

/**
 * Render inside a MemoryRouter so Link / useNavigate / useLocation work.
 *
 * @param {React.ReactElement} ui
 * @param {{ initialEntries?: string[] }} options
 */
export function renderWithRouter(ui, { initialEntries = ['/'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>,
  );
}

// Re-export everything from RTL so tests can do:
//   import { screen, fireEvent } from '../test-utils'
export * from '@testing-library/react';
