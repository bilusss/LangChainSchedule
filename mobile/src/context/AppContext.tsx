/**
 * App Context - globalny stan aplikacji
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import apiService from '../services/api';

// Typy
interface UserPreferences {
  sleepSchedule: string;
  deepWorkWindows: string;
  studyBlockDuration: string;
  habits: string;
}

interface AppState {
  isConnected: boolean;
  apiUrl: string;
  preferences: UserPreferences;
  conversationId: string | null;
  isLoading: boolean;
}

interface AppContextType extends AppState {
  setApiUrl: (url: string) => Promise<void>;
  setPreferences: (prefs: Partial<UserPreferences>) => Promise<void>;
  setConversationId: (id: string | null) => void;
  checkConnection: () => Promise<boolean>;
  setIsLoading: (loading: boolean) => void;
}

// Default values
const defaultPreferences: UserPreferences = {
  sleepSchedule: '23:00 - 7:00',
  deepWorkWindows: '9:00-12:00, 15:00-18:00',
  studyBlockDuration: '1.5h',
  habits: 'Śniadanie 7:30, Obiad 13:00, Kolacja 19:00',
};

const defaultState: AppState = {
  isConnected: false,
  apiUrl: 'http://localhost:8000',
  preferences: defaultPreferences,
  conversationId: null,
  isLoading: false,
};

// Context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(defaultState);

  // Załaduj zapisane dane przy starcie
  useEffect(() => {
    loadSavedData();
  }, []);

  const loadSavedData = async () => {
    try {
      const [savedUrl, savedPrefs] = await Promise.all([
        AsyncStorage.getItem('api_base_url'),
        AsyncStorage.getItem('user_preferences'),
      ]);

      const newState: Partial<AppState> = {};

      if (savedUrl) {
        newState.apiUrl = savedUrl;
        apiService.setBaseUrl(savedUrl);
      }

      if (savedPrefs) {
        newState.preferences = { ...defaultPreferences, ...JSON.parse(savedPrefs) };
      }

      setState((prev) => ({ ...prev, ...newState }));

      // Sprawdź połączenie
      checkConnection();
    } catch (error) {
      console.error('Error loading saved data:', error);
    }
  };

  const setApiUrl = async (url: string) => {
    apiService.setBaseUrl(url);
    setState((prev) => ({ ...prev, apiUrl: url }));
    await AsyncStorage.setItem('api_base_url', url);
    await checkConnection();
  };

  const setPreferences = async (prefs: Partial<UserPreferences>) => {
    const newPrefs = { ...state.preferences, ...prefs };
    setState((prev) => ({ ...prev, preferences: newPrefs }));
    await AsyncStorage.setItem('user_preferences', JSON.stringify(newPrefs));
  };

  const setConversationId = (id: string | null) => {
    setState((prev) => ({ ...prev, conversationId: id }));
  };

  const setIsLoading = (loading: boolean) => {
    setState((prev) => ({ ...prev, isLoading: loading }));
  };

  const checkConnection = async (): Promise<boolean> => {
    try {
      const isHealthy = await apiService.healthCheck();
      setState((prev) => ({ ...prev, isConnected: isHealthy }));
      return isHealthy;
    } catch (error) {
      setState((prev) => ({ ...prev, isConnected: false }));
      return false;
    }
  };

  const contextValue: AppContextType = {
    ...state,
    setApiUrl,
    setPreferences,
    setConversationId,
    checkConnection,
    setIsLoading,
  };

  return <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>;
}

// Hook
export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

export default AppContext;
