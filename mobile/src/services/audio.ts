/**
 * Audio Recording Service - nagrywanie i transkrypcja głosu
 */

import { Audio } from 'expo-av';
import apiService from './api';

export interface RecordingResult {
  text: string;
  duration: number;
  success: boolean;
  error?: string;
}

class AudioService {
  private recording: Audio.Recording | null = null;
  private isRecording: boolean = false;
  private startTime: number = 0;

  /**
   * Sprawdza i prosi o uprawnienia do mikrofonu
   */
  async requestPermissions(): Promise<boolean> {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      return status === 'granted';
    } catch (error) {
      console.error('Error requesting permissions:', error);
      return false;
    }
  }

  /**
   * Rozpoczyna nagrywanie
   */
  async startRecording(): Promise<boolean> {
    try {
      // Sprawdź uprawnienia
      const hasPermission = await this.requestPermissions();
      if (!hasPermission) {
        console.error('No microphone permission');
        return false;
      }

      // Konfiguracja audio
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      // Utwórz nowe nagranie
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      this.recording = recording;
      this.isRecording = true;
      this.startTime = Date.now();

      console.log('Recording started');
      return true;
    } catch (error) {
      console.error('Error starting recording:', error);
      return false;
    }
  }

  /**
   * Zatrzymuje nagrywanie i zwraca transkrypcję
   */
  async stopRecording(): Promise<RecordingResult> {
    if (!this.recording) {
      return {
        text: '',
        duration: 0,
        success: false,
        error: 'No active recording',
      };
    }

    try {
      const duration = (Date.now() - this.startTime) / 1000;

      // Zatrzymaj nagrywanie
      await this.recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });

      // Pobierz URI nagrania
      const uri = this.recording.getURI();
      this.recording = null;
      this.isRecording = false;

      if (!uri) {
        return {
          text: '',
          duration,
          success: false,
          error: 'No recording URI',
        };
      }

      console.log('Recording stopped, URI:', uri);

      // Wyślij plik jako multipart/form-data (profesjonalny sposób)
      console.log('Sending audio file for transcription...');
      const result = await apiService.transcribeAudioFile(uri, 'pl');

      return {
        text: result.text,
        duration,
        success: true,
      };
    } catch (error) {
      console.error('Error stopping recording:', error);
      this.recording = null;
      this.isRecording = false;

      return {
        text: '',
        duration: 0,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Anuluje nagrywanie
   */
  async cancelRecording(): Promise<void> {
    if (this.recording) {
      try {
        await this.recording.stopAndUnloadAsync();
        // Plik tymczasowy zostanie usunięty automatycznie przez system
      } catch (error) {
        console.error('Error canceling recording:', error);
      }
      this.recording = null;
      this.isRecording = false;
    }
  }

  /**
   * Sprawdza czy trwa nagrywanie
   */
  getIsRecording(): boolean {
    return this.isRecording;
  }

  /**
   * Zwraca czas trwania aktualnego nagrania w sekundach
   */
  getRecordingDuration(): number {
    if (!this.isRecording) return 0;
    return (Date.now() - this.startTime) / 1000;
  }
}

// Singleton instance
export const audioService = new AudioService();
export default audioService;
