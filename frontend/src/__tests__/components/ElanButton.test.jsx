import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ElanButton from '../../components/ui/ElanButton';

describe('ElanButton', () => {
  it('renders its children', () => {
    render(<ElanButton>Click me</ElanButton>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('shows a spinner and hides text when loading', () => {
    render(<ElanButton loading>Submit</ElanButton>);
    // text is replaced by spinner — no "Submit" visible
    expect(screen.queryByText('Submit')).not.toBeInTheDocument();
    // the button element itself is still present
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('is disabled when the disabled prop is set', () => {
    render(<ElanButton disabled>Click</ElanButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('is disabled when loading', () => {
    render(<ElanButton loading>Click</ElanButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('calls onClick when clicked', () => {
    const handler = vi.fn();
    render(<ElanButton onClick={handler}>Go</ElanButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const handler = vi.fn();
    render(<ElanButton onClick={handler} disabled>Go</ElanButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(handler).not.toHaveBeenCalled();
  });

  it('applies type="submit" when specified', () => {
    render(<ElanButton type="submit">Save</ElanButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });

  it('defaults to type="button"', () => {
    render(<ElanButton>Click</ElanButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });
});
