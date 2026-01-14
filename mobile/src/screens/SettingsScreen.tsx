/**
 * Settings Screen - ustawienia aplikacji
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

import { useApp } from '../context/AppContext';

// Theme
const theme = {
  primary: '#6366f1',
  background: '#0f0f23',
  card: '#1a1a2e',
  text: '#ffffff',
  textSecondary: '#a0a0b0',
  accent: '#22d3ee',
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
};

export default function SettingsScreen() {
  const {
    apiUrl,
    setApiUrl,
    preferences,
    setPreferences,
    isConnected,
    checkConnection,
  } = useApp();

  const [tempApiUrl, setTempApiUrl] = useState(apiUrl);
  const [tempPreferences, setTempPreferences] = useState(preferences);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setTempApiUrl(apiUrl);
  }, [apiUrl]);

  useEffect(() => {
    setTempPreferences(preferences);
  }, [preferences]);

  // Test połączenia
  const testConnection = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setIsTestingConnection(true);

    try {
      // Tymczasowo ustaw URL
      await setApiUrl(tempApiUrl);
      const success = await checkConnection();

      if (success) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        Alert.alert('Sukces', 'Połączenie z serwerem działa prawidłowo! ✅');
      } else {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        Alert.alert('Błąd', 'Nie udało się połączyć z serwerem. Sprawdź adres URL.');
      }
    } catch (error) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      Alert.alert('Błąd', 'Wystąpił błąd podczas testowania połączenia.');
    } finally {
      setIsTestingConnection(false);
    }
  };

  // Zapisz ustawienia
  const saveSettings = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setIsSaving(true);

    try {
      await setApiUrl(tempApiUrl);
      await setPreferences(tempPreferences);
      
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert('Zapisano', 'Ustawienia zostały zapisane.');
    } catch (error) {
      Alert.alert('Błąd', 'Nie udało się zapisać ustawień.');
    } finally {
      setIsSaving(false);
    }
  };

  // Reset do domyślnych
  const resetToDefaults = () => {
    Alert.alert(
      'Reset ustawień',
      'Czy na pewno chcesz przywrócić domyślne ustawienia?',
      [
        { text: 'Anuluj', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            setTempPreferences({
              sleepSchedule: '23:00 - 7:00',
              deepWorkWindows: '9:00-12:00, 15:00-18:00',
              studyBlockDuration: '1.5h',
              habits: 'Śniadanie 7:30, Obiad 13:00, Kolacja 19:00',
            });
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Status połączenia */}
      <View style={styles.statusCard}>
        <View style={styles.statusRow}>
          <Ionicons
            name={isConnected ? 'cloud-done' : 'cloud-offline'}
            size={24}
            color={isConnected ? theme.success : theme.error}
          />
          <View style={styles.statusText}>
            <Text style={styles.statusTitle}>
              {isConnected ? 'Połączono z serwerem' : 'Brak połączenia'}
            </Text>
            <Text style={styles.statusSubtitle}>{apiUrl}</Text>
          </View>
        </View>
      </View>

      {/* Sekcja: Serwer API */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🌐 Serwer API</Text>
        <Text style={styles.sectionHint}>
          Adres URL backendu Python. Jeśli używasz Expo Go na telefonie, 
          użyj IP komputera zamiast localhost (np. http://192.168.1.100:8000)
        </Text>
        
        <TextInput
          style={styles.input}
          value={tempApiUrl}
          onChangeText={setTempApiUrl}
          placeholder="http://localhost:8000"
          placeholderTextColor={theme.textSecondary}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
        
        <TouchableOpacity
          style={styles.testButton}
          onPress={testConnection}
          disabled={isTestingConnection}
        >
          {isTestingConnection ? (
            <ActivityIndicator size="small" color={theme.text} />
          ) : (
            <>
              <Ionicons name="flash-outline" size={20} color={theme.text} />
              <Text style={styles.testButtonText}>Testuj połączenie</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Sekcja: Preferencje planowania */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>⚙️ Preferencje planowania</Text>
        <Text style={styles.sectionHint}>
          Te ustawienia są używane przez AI Planner do tworzenia optymalnego harmonogramu
        </Text>

        <View style={styles.prefGroup}>
          <Text style={styles.prefLabel}>🛏️ Godziny snu</Text>
          <TextInput
            style={styles.prefInput}
            value={tempPreferences.sleepSchedule}
            onChangeText={(text) =>
              setTempPreferences({ ...tempPreferences, sleepSchedule: text })
            }
            placeholder="23:00 - 7:00"
            placeholderTextColor={theme.textSecondary}
          />
        </View>

        <View style={styles.prefGroup}>
          <Text style={styles.prefLabel}>🧠 Okna Deep Work</Text>
          <TextInput
            style={styles.prefInput}
            value={tempPreferences.deepWorkWindows}
            onChangeText={(text) =>
              setTempPreferences({ ...tempPreferences, deepWorkWindows: text })
            }
            placeholder="9:00-12:00, 15:00-18:00"
            placeholderTextColor={theme.textSecondary}
          />
        </View>

        <View style={styles.prefGroup}>
          <Text style={styles.prefLabel}>📚 Długość bloku nauki</Text>
          <TextInput
            style={styles.prefInput}
            value={tempPreferences.studyBlockDuration}
            onChangeText={(text) =>
              setTempPreferences({ ...tempPreferences, studyBlockDuration: text })
            }
            placeholder="1.5h"
            placeholderTextColor={theme.textSecondary}
          />
        </View>

        <View style={styles.prefGroup}>
          <Text style={styles.prefLabel}>🍽️ Stałe nawyki</Text>
          <TextInput
            style={[styles.prefInput, styles.prefInputMultiline]}
            value={tempPreferences.habits}
            onChangeText={(text) =>
              setTempPreferences({ ...tempPreferences, habits: text })
            }
            placeholder="Śniadanie 7:30, Obiad 13:00, Kolacja 19:00"
            placeholderTextColor={theme.textSecondary}
            multiline
            numberOfLines={3}
          />
        </View>

        <TouchableOpacity style={styles.resetButton} onPress={resetToDefaults}>
          <Ionicons name="refresh-outline" size={18} color={theme.textSecondary} />
          <Text style={styles.resetButtonText}>Przywróć domyślne</Text>
        </TouchableOpacity>
      </View>

      {/* Przycisk zapisz */}
      <TouchableOpacity
        style={styles.saveButton}
        onPress={saveSettings}
        disabled={isSaving}
      >
        {isSaving ? (
          <ActivityIndicator size="small" color={theme.text} />
        ) : (
          <>
            <Ionicons name="save-outline" size={24} color={theme.text} />
            <Text style={styles.saveButtonText}>Zapisz ustawienia</Text>
          </>
        )}
      </TouchableOpacity>

      {/* Info */}
      <View style={styles.infoSection}>
        <Text style={styles.infoTitle}>ℹ️ Informacje</Text>
        <Text style={styles.infoText}>
          • Speech-to-text: Whisper Large V3 (GROQ){'\n'}
          • Planner AI: GROQ qwen/qwen3-32b{'\n'}
          • Chat: Gemini / OpenAI{'\n'}
          • Kalendarz: Google Calendar API
        </Text>
        <Text style={styles.version}>Calendar AI v1.0.0</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  statusCard: {
    backgroundColor: theme.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  statusText: {
    flex: 1,
  },
  statusTitle: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '600',
  },
  statusSubtitle: {
    color: theme.textSecondary,
    fontSize: 13,
    marginTop: 2,
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 8,
  },
  sectionHint: {
    fontSize: 13,
    color: theme.textSecondary,
    lineHeight: 18,
    marginBottom: 16,
  },
  input: {
    backgroundColor: theme.card,
    borderRadius: 12,
    padding: 16,
    color: theme.text,
    fontSize: 16,
    marginBottom: 12,
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.accent,
    padding: 14,
    borderRadius: 12,
    gap: 8,
  },
  testButtonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: '600',
  },
  prefGroup: {
    marginBottom: 16,
  },
  prefLabel: {
    color: theme.text,
    fontSize: 15,
    fontWeight: '500',
    marginBottom: 8,
  },
  prefInput: {
    backgroundColor: theme.card,
    borderRadius: 12,
    padding: 14,
    color: theme.text,
    fontSize: 15,
  },
  prefInputMultiline: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    gap: 8,
  },
  resetButtonText: {
    color: theme.textSecondary,
    fontSize: 14,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.primary,
    padding: 18,
    borderRadius: 16,
    gap: 12,
    marginBottom: 32,
  },
  saveButtonText: {
    color: theme.text,
    fontSize: 18,
    fontWeight: '600',
  },
  infoSection: {
    backgroundColor: theme.card,
    borderRadius: 16,
    padding: 20,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 12,
  },
  infoText: {
    fontSize: 13,
    color: theme.textSecondary,
    lineHeight: 22,
  },
  version: {
    fontSize: 12,
    color: theme.textSecondary,
    marginTop: 16,
    textAlign: 'center',
    opacity: 0.6,
  },
});
