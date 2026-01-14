/**
 * API Service - komunikacja z backendem Python
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Typ dla konfiguracji API
interface ApiConfig {
  baseUrl: string;
  timeout: number;
}

// Typy odpowiedzi
export interface ChatResponse {
  response: string;
  conversation_id: string;
}

export interface PlanResponse {
  events: PlanEvent[];
  conflicts: PlanConflict[];
  reasoning: string;
  display_text: string;
}

export interface PlanEvent {
  action: 'create' | 'update';
  summary: string;
  start: string;
  end: string;
  description?: string;
  event_id?: string;
  reason?: string;
}

export interface PlanConflict {
  existing_event: string;
  conflict_time: string;
  suggestion: string;
}

export interface ExecuteResult {
  success: boolean;
  total: number;
  succeeded: number;
  results: Array<{
    event: string;
    status: 'created' | 'updated' | 'error';
    result?: string;
    error?: string;
  }>;
}

export interface TranscribeResponse {
  text: string;
  language: string;
}

// Klasa API Service
class ApiService {
  private client: AxiosInstance;
  private baseUrl: string = 'http://localhost:8000';

  constructor() {
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 60000, // 60s timeout (transkrypcja może trwać)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor do logowania błędów
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.message);
        if (error.response) {
          console.error('Response data:', error.response.data);
        }
        return Promise.reject(error);
      }
    );

    // Załaduj zapisany URL
    this.loadBaseUrl();
  }

  private async loadBaseUrl() {
    try {
      const savedUrl = await AsyncStorage.getItem('api_base_url');
      if (savedUrl) {
        this.setBaseUrl(savedUrl);
      }
    } catch (error) {
      console.error('Error loading base URL:', error);
    }
  }

  public setBaseUrl(url: string) {
    this.baseUrl = url;
    this.client.defaults.baseURL = url;
    AsyncStorage.setItem('api_base_url', url);
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.data.status === 'ok';
    } catch (error) {
      return false;
    }
  }

  // ============================================================================
  // CALENDAR
  // ============================================================================

  async getCalendarEvents(daysAhead: number = 7, maxResults: number = 20): Promise<string> {
    const response = await this.client.get('/calendar/events', {
      params: { days_ahead: daysAhead, max_results: maxResults },
    });
    return response.data.data;
  }

  async createCalendarEvent(
    summary: string,
    startTime: string,
    endTime: string,
    description: string = '',
    location: string = ''
  ): Promise<string> {
    const response = await this.client.post('/calendar/events', {
      summary,
      start_time: startTime,
      end_time: endTime,
      description,
      location,
    });
    return response.data.data;
  }

  async updateCalendarEvent(
    eventId: string,
    updates: {
      summary?: string;
      startTime?: string;
      endTime?: string;
      description?: string;
      location?: string;
    }
  ): Promise<string> {
    const response = await this.client.put('/calendar/events', {
      event_id: eventId,
      summary: updates.summary,
      start_time: updates.startTime,
      end_time: updates.endTime,
      description: updates.description,
      location: updates.location,
    });
    return response.data.data;
  }

  async deleteCalendarEvent(eventId: string): Promise<string> {
    const response = await this.client.delete(`/calendar/events/${eventId}`);
    return response.data.data;
  }

  // ============================================================================
  // CHAT
  // ============================================================================

  async sendMessage(
    message: string,
    conversationId?: string
  ): Promise<ChatResponse> {
    const response = await this.client.post('/chat', {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  }

  async clearConversation(conversationId: string): Promise<void> {
    await this.client.delete(`/chat/${conversationId}`);
  }

  // ============================================================================
  // PLANNER
  // ============================================================================

  async generatePlan(
    tasks: string[],
    preferences?: {
      sleepSchedule?: string;
      deepWorkWindows?: string;
      studyBlockDuration?: string;
      habits?: string;
    }
  ): Promise<PlanResponse> {
    const response = await this.client.post('/planner/generate', {
      tasks,
      sleep_schedule: preferences?.sleepSchedule || '23:00 - 7:00',
      deep_work_windows: preferences?.deepWorkWindows || '9:00-12:00, 15:00-18:00',
      study_block_duration: preferences?.studyBlockDuration || '1.5h',
      habits: preferences?.habits || 'Śniadanie 7:30, Obiad 13:00, Kolacja 19:00',
    });
    return response.data;
  }

  async executePlan(events: PlanEvent[]): Promise<ExecuteResult> {
    const response = await this.client.post('/planner/execute', { events });
    return response.data;
  }

  // ============================================================================
  // SPEECH TO TEXT
  // ============================================================================

  async transcribeAudio(audioBase64: string, language: string = 'pl'): Promise<TranscribeResponse> {
    const response = await this.client.post('/transcribe', {
      audio_base64: audioBase64,
      language,
    });
    return response.data;
  }

  /**
   * Transkrypcja audio przez multipart form-data (profesjonalne podejście)
   * Nie wymaga konwersji na base64, bezpośredni upload pliku
   */
  async transcribeAudioFile(fileUri: string, language: string = 'pl'): Promise<TranscribeResponse> {
    const formData = new FormData();
    
    // React Native automatycznie obsługuje file URI w FormData
    formData.append('file', {
      uri: fileUri,
      type: 'audio/m4a',
      name: 'recording.m4a',
    } as any);
    
    formData.append('language', language);

    const response = await fetch(`${this.baseUrl}/transcribe`, {
      method: 'POST',
      body: formData,
      headers: {
        // Nie ustawiaj Content-Type - fetch sam ustawi z boundary
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Transcription failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }
}

// Singleton instance
export const apiService = new ApiService();
export default apiService;
