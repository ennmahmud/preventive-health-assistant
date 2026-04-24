export default function ElanIcon({ size = 40 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none" aria-hidden="true">
      <rect width="52" height="52" rx="12" fill="var(--elan-ch-800)" />
      <polyline
        points="8,26 17,26 20,14 24,38 27,26 44,26"
        stroke="white" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
