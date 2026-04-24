import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import useChat from '../../hooks/useChat';

// ── Mock API utilities ────────────────────────────────────────────────────────
const mockSendChatMessage = vi.fn();
const mockDeleteSession   = vi.fn();

vi.mock('../../utils/api', () => ({
  sendChatMessage: (...a) => mockSendChatMessage(...a),
  deleteSession:   (...a) => mockDeleteSession(...a),
}));

describe('useChat', () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Initial state ────────────────────────────────────────────────────────
  it('starts with empty messages and no session', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
    expect(result.current.sessionId).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.lastResult).toBeNull();
  });

  // ── send ─────────────────────────────────────────────────────────────────
  it('send: appends the user message immediately', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_1',
      reply: 'Hello!',
      assessment_complete: false,
      result: null,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Hi there'));

    const msgs = result.current.messages;
    expect(msgs[0]).toMatchObject({ role: 'user', content: 'Hi there' });
  });

  it('send: appends the assistant reply after API response', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_1',
      reply: 'Your risk is low.',
      assessment_complete: false,
      result: null,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Check my risk'));

    const msgs = result.current.messages;
    expect(msgs[1]).toMatchObject({ role: 'assistant', content: 'Your risk is low.' });
  });

  it('send: stores the session ID returned by the API', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_abc',
      reply: 'OK',
      assessment_complete: false,
      result: null,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Hello'));
    expect(result.current.sessionId).toBe('sess_abc');
  });

  it('send: passes existing sessionId to subsequent API calls', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_abc',
      reply: 'OK',
      assessment_complete: false,
      result: null,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('First message'));
    await act(() => result.current.send('Second message'));

    // Second call should pass the session ID obtained from the first
    expect(mockSendChatMessage).toHaveBeenNthCalledWith(
      2,
      'Second message',
      'sess_abc',
      null,
      null,
    );
  });

  it('send: sets lastResult when assessment_complete is true', async () => {
    const fakeResult = { risk_probability: 0.72, risk_category: 'High' };
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_1',
      reply: 'Assessment complete.',
      assessment_complete: true,
      result: fakeResult,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Assess me'));
    expect(result.current.lastResult).toEqual(fakeResult);
  });

  it('send: does not set lastResult when assessment is not complete', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_1',
      reply: 'How old are you?',
      assessment_complete: false,
      result: null,
    });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Check diabetes'));
    expect(result.current.lastResult).toBeNull();
  });

  it('send: ignores empty or whitespace-only input', async () => {
    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('   '));
    expect(mockSendChatMessage).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  // ── error handling ───────────────────────────────────────────────────────
  it('send: adds an error message and sets error state on failure', async () => {
    mockSendChatMessage.mockRejectedValue(new Error('Network failure'));

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Hello'));

    expect(result.current.error).toBe('Network failure');
    const msgs = result.current.messages;
    // user message + error bot message
    expect(msgs).toHaveLength(2);
    expect(msgs[1].isError).toBe(true);
    expect(msgs[1].role).toBe('assistant');
  });

  it('send: clears previous error on the next attempt', async () => {
    mockSendChatMessage
      .mockRejectedValueOnce(new Error('Timeout'))
      .mockResolvedValue({ session_id: 's', reply: 'OK', assessment_complete: false, result: null });

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('First'));
    expect(result.current.error).toBe('Timeout');

    await act(() => result.current.send('Retry'));
    expect(result.current.error).toBeNull();
  });

  // ── reset ────────────────────────────────────────────────────────────────
  it('reset: clears all state', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_z',
      reply: 'Hi',
      assessment_complete: false,
      result: null,
    });
    mockDeleteSession.mockResolvedValue(undefined);

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Hello'));
    expect(result.current.messages).toHaveLength(2);

    await act(() => result.current.reset());
    expect(result.current.messages).toHaveLength(0);
    expect(result.current.sessionId).toBeNull();
    expect(result.current.lastResult).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('reset: calls deleteSession with the active session ID', async () => {
    mockSendChatMessage.mockResolvedValue({
      session_id: 'sess_z',
      reply: 'Hi',
      assessment_complete: false,
      result: null,
    });
    mockDeleteSession.mockResolvedValue(undefined);

    const { result } = renderHook(() => useChat());
    await act(() => result.current.send('Hello'));
    await act(() => result.current.reset());

    expect(mockDeleteSession).toHaveBeenCalledWith('sess_z');
  });

  it('reset: skips deleteSession when there is no active session', async () => {
    const { result } = renderHook(() => useChat());
    await act(() => result.current.reset());
    expect(mockDeleteSession).not.toHaveBeenCalled();
  });
});
