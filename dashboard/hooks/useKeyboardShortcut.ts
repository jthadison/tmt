/**
 * Keyboard Shortcut Hook
 * Generic hook for handling keyboard shortcuts
 */

import { useEffect } from 'react';

interface UseKeyboardShortcutOptions {
  enabled?: boolean;
}

/**
 * Hook to handle keyboard shortcuts
 * @param keys Array of keys that need to be pressed together
 * @param callback Function to call when shortcut is triggered
 * @param options Optional configuration
 */
export function useKeyboardShortcut(
  keys: string[],
  callback: () => void,
  options?: UseKeyboardShortcutOptions
): void {
  useEffect(() => {
    if (options?.enabled === false) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const modifiers = ['Control', 'Shift', 'Alt', 'Meta'];
      const isModifier = (key: string) => modifiers.includes(key);

      const pressedKeys: string[] = [
        event.ctrlKey && 'Control',
        event.shiftKey && 'Shift',
        event.altKey && 'Alt',
        event.metaKey && 'Meta',
        !isModifier(event.key) && event.key.toUpperCase(),
      ].filter(Boolean) as string[];

      const targetKeys = keys.map((k) => k.toUpperCase());

      if (
        pressedKeys.length === targetKeys.length &&
        pressedKeys.every((k) => targetKeys.includes(k))
      ) {
        event.preventDefault();
        callback();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keys, callback, options]);
}
