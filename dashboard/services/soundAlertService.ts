/**
 * Sound alert service for notification audio
 * Uses Web Audio API to play notification sounds
 */

import { NotificationPriority } from '@/types/notifications'

class SoundAlertService {
  private audioContext: AudioContext | null = null
  private soundCache: Map<string, AudioBuffer> = new Map()

  /**
   * Initialize audio context
   */
  private getAudioContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)()
    }
    return this.audioContext
  }

  /**
   * Generate a simple beep sound using oscillator
   */
  private async generateBeep(
    frequency: number,
    duration: number,
    volume: number
  ): Promise<void> {
    const audioContext = this.getAudioContext()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    oscillator.frequency.value = frequency
    oscillator.type = 'sine'
    gainNode.gain.value = volume

    const now = audioContext.currentTime
    gainNode.gain.setValueAtTime(volume, now)
    gainNode.gain.exponentialRampToValueAtTime(0.01, now + duration)

    oscillator.start(now)
    oscillator.stop(now + duration)

    return new Promise((resolve) => {
      setTimeout(resolve, duration * 1000)
    })
  }

  /**
   * Play a notification sound for a given priority
   */
  async playNotificationSound(
    priority: NotificationPriority,
    soundName: string,
    volume: number
  ): Promise<void> {
    try {
      // For now, use simple oscillator-based sounds
      // In production, you could load actual audio files
      const soundConfig = this.getSoundConfig(priority, soundName)
      await this.generateBeep(
        soundConfig.frequency,
        soundConfig.duration,
        volume / 100
      )
    } catch (error) {
      console.error('Error playing sound:', error)
    }
  }

  /**
   * Get sound configuration based on priority and sound name
   */
  private getSoundConfig(
    priority: NotificationPriority,
    soundName: string
  ): { frequency: number; duration: number } {
    // Critical sounds
    if (priority === NotificationPriority.CRITICAL) {
      if (soundName === 'critical-alarm') {
        return { frequency: 1000, duration: 0.4 }
      }
      if (soundName === 'critical-siren') {
        return { frequency: 1200, duration: 0.5 }
      }
      return { frequency: 880, duration: 0.3 } // critical-beep (default)
    }

    // Warning sounds
    if (priority === NotificationPriority.WARNING) {
      if (soundName === 'warning-chime') {
        return { frequency: 700, duration: 0.25 }
      }
      if (soundName === 'warning-ding') {
        return { frequency: 800, duration: 0.2 }
      }
      return { frequency: 659, duration: 0.2 } // warning-beep (default)
    }

    // Success sounds
    if (priority === NotificationPriority.SUCCESS) {
      if (soundName === 'success-ding') {
        return { frequency: 550, duration: 0.15 }
      }
      if (soundName === 'success-tada') {
        return { frequency: 600, duration: 0.3 }
      }
      return { frequency: 523, duration: 0.2 } // success-chime (default)
    }

    // Info sounds (default)
    if (soundName === 'info-pop') {
      return { frequency: 450, duration: 0.1 }
    }
    if (soundName === 'info-gentle') {
      return { frequency: 400, duration: 0.15 }
    }
    return { frequency: 440, duration: 0.15 } // info-notification (default)
  }

  /**
   * Play a preview sound
   */
  async playPreview(priority: NotificationPriority, volume: number): Promise<void> {
    const soundConfig = this.getSoundConfig(priority, 'default')
    await this.generateBeep(soundConfig.frequency, soundConfig.duration, volume / 100)
  }

  /**
   * Cleanup audio context
   */
  cleanup(): void {
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close()
      this.audioContext = null
    }
    this.soundCache.clear()
  }
}

// Singleton instance
export const soundAlertService = new SoundAlertService()
