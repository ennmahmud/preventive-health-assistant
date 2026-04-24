import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RiskRing from '../../components/health/RiskRing';

describe('RiskRing', () => {
  it('displays the probability as a percentage', () => {
    render(<RiskRing probability={0.73} risk_level="high" />);
    expect(screen.getByText('73%')).toBeInTheDocument();
  });

  it('rounds to nearest integer', () => {
    render(<RiskRing probability={0.456} risk_level="moderate" />);
    expect(screen.getByText('46%')).toBeInTheDocument();
  });

  it('clamps probability above 1 to 100%', () => {
    render(<RiskRing probability={1.5} risk_level="very_high" />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('clamps negative probability to 0%', () => {
    render(<RiskRing probability={-0.1} risk_level="low" />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('renders the condition name when provided', () => {
    render(<RiskRing probability={0.3} risk_level="moderate" condition="Diabetes" />);
    expect(screen.getByText('Diabetes')).toBeInTheDocument();
  });

  it('renders the risk level label when condition is provided', () => {
    render(<RiskRing probability={0.3} risk_level="moderate" condition="CVD" />);
    expect(screen.getByText('Moderate')).toBeInTheDocument();
  });

  it('does not render condition text when condition is empty', () => {
    const { container } = render(<RiskRing probability={0.5} risk_level="high" />);
    // only the % label and "risk" sub-label should appear — no condition section
    expect(screen.queryByText('High')).not.toBeInTheDocument();
    expect(container.querySelectorAll('svg')).toHaveLength(1);
  });

  it('renders two SVG circles (track + fill)', () => {
    const { container } = render(<RiskRing probability={0.4} risk_level="moderate" />);
    expect(container.querySelectorAll('circle')).toHaveLength(2);
  });
});
