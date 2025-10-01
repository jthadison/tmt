/**
 * Tests for useKeyboardShortcut hook
 */

import { renderHook } from '@testing-library/react';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';

describe('useKeyboardShortcut', () => {
  it('should trigger callback when shortcut is pressed', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut(['Control', 'Shift', 'S'], callback));

    // Simulate Ctrl+Shift+S
    const event = new KeyboardEvent('keydown', {
      bubbles: true,
      cancelable: true,
      ctrlKey: true,
      shiftKey: true,
      key: 'S',
    });

    // Add preventDefault mock
    const preventDefaultSpy = jest.spyOn(event, 'preventDefault');

    window.dispatchEvent(event);

    expect(callback).toHaveBeenCalledTimes(1);
    expect(preventDefaultSpy).toHaveBeenCalled();
  });

  it('should not trigger callback when wrong keys are pressed', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut(['Control', 'Shift', 'S'], callback));

    // Simulate just Ctrl+S (missing Shift)
    const event = new KeyboardEvent('keydown', {
      ctrlKey: true,
      key: 'S',
    });

    window.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });

  it('should not trigger when disabled', () => {
    const callback = jest.fn();
    renderHook(() => useKeyboardShortcut(['Control', 'Shift', 'S'], callback, { enabled: false }));

    const event = new KeyboardEvent('keydown', {
      ctrlKey: true,
      shiftKey: true,
      key: 'S',
    });

    window.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });

  it('should clean up event listener on unmount', () => {
    const callback = jest.fn();
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

    const { unmount } = renderHook(() =>
      useKeyboardShortcut(['Control', 'Shift', 'S'], callback)
    );

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
  });
});
