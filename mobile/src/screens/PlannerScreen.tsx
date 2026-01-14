/**
 * Planner Screen - AI Planner z GROQ
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

import { useApp } from '../context/AppContext';
import apiService, { PlanEvent, PlanResponse } from '../services/api';

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

type Step = 'input' | 'loading' | 'review' | 'executing' | 'done';

export default function PlannerScreen() {
  const { preferences } = useApp();
  
  const [step, setStep] = useState<Step>('input');
  const [tasks, setTasks] = useState<string[]>(['']);
  const [generatedPlan, setGeneratedPlan] = useState<PlanResponse | null>(null);
  const [selectedEvents, setSelectedEvents] = useState<Set<number>>(new Set());
  const [executionResults, setExecutionResults] = useState<string[]>([]);

  // Dodaj nowe zadanie
  const addTask = () => {
    setTasks([...tasks, '']);
  };

  // Aktualizuj zadanie
  const updateTask = (index: number, text: string) => {
    const newTasks = [...tasks];
    newTasks[index] = text;
    setTasks(newTasks);
  };

  // Usuń zadanie
  const removeTask = (index: number) => {
    if (tasks.length > 1) {
      const newTasks = tasks.filter((_, i) => i !== index);
      setTasks(newTasks);
    }
  };

  // Generuj plan
  const generatePlan = async () => {
    const validTasks = tasks.filter((t) => t.trim());
    
    if (validTasks.length === 0) {
      Alert.alert('Błąd', 'Dodaj przynajmniej jedno zadanie');
      return;
    }

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setStep('loading');

    try {
      const plan = await apiService.generatePlan(validTasks, {
        sleepSchedule: preferences.sleepSchedule,
        deepWorkWindows: preferences.deepWorkWindows,
        studyBlockDuration: preferences.studyBlockDuration,
        habits: preferences.habits,
      });

      setGeneratedPlan(plan);
      
      // Domyślnie zaznacz wszystkie wydarzenia
      setSelectedEvents(new Set(plan.events.map((_, i) => i)));
      
      setStep('review');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (error) {
      console.error('Error generating plan:', error);
      Alert.alert('Błąd', 'Nie udało się wygenerować planu. Sprawdź połączenie z serwerem.');
      setStep('input');
    }
  };

  // Toggle zaznaczenia wydarzenia
  const toggleEvent = (index: number) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const newSelected = new Set(selectedEvents);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedEvents(newSelected);
  };

  // Wykonaj plan
  const executePlan = async () => {
    if (!generatedPlan || selectedEvents.size === 0) {
      Alert.alert('Błąd', 'Zaznacz przynajmniej jedno wydarzenie');
      return;
    }

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    setStep('executing');

    try {
      const eventsToExecute = generatedPlan.events.filter((_, i) => selectedEvents.has(i));
      const result = await apiService.executePlan(eventsToExecute);

      const resultMessages = result.results.map((r) => {
        if (r.status === 'created') {
          return `✅ Utworzono: ${r.event}`;
        } else if (r.status === 'updated') {
          return `🔄 Zaktualizowano: ${r.event}`;
        } else {
          return `❌ Błąd: ${r.event} - ${r.error}`;
        }
      });

      setExecutionResults(resultMessages);
      setStep('done');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (error) {
      console.error('Error executing plan:', error);
      Alert.alert('Błąd', 'Nie udało się wykonać planu');
      setStep('review');
    }
  };

  // Reset
  const reset = () => {
    setStep('input');
    setTasks(['']);
    setGeneratedPlan(null);
    setSelectedEvents(new Set());
    setExecutionResults([]);
  };

  // Formatowanie daty
  const formatDateTime = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('pl-PL', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  // Render wydarzenia w preview
  const renderEventPreview = (event: PlanEvent, index: number) => {
    const isSelected = selectedEvents.has(index);
    const isUpdate = event.action === 'update';

    return (
      <TouchableOpacity
        key={index}
        style={[styles.eventPreview, isSelected && styles.eventPreviewSelected]}
        onPress={() => toggleEvent(index)}
        activeOpacity={0.7}
      >
        <View style={styles.eventCheckbox}>
          <Ionicons
            name={isSelected ? 'checkbox' : 'square-outline'}
            size={24}
            color={isSelected ? theme.success : theme.textSecondary}
          />
        </View>
        
        <View style={styles.eventPreviewContent}>
          <View style={styles.eventPreviewHeader}>
            {isUpdate && (
              <View style={styles.updateBadge}>
                <Ionicons name="refresh" size={12} color={theme.warning} />
                <Text style={styles.updateBadgeText}>Modyfikacja</Text>
              </View>
            )}
            <Text style={styles.eventPreviewTitle}>{event.summary}</Text>
          </View>
          
          <Text style={styles.eventPreviewTime}>
            {formatDateTime(event.start)} → {formatDateTime(event.end)}
          </Text>
          
          {event.description && (
            <Text style={styles.eventPreviewDesc} numberOfLines={2}>
              {event.description}
            </Text>
          )}
          
          {event.reason && (
            <Text style={styles.eventPreviewReason}>
              💡 {event.reason}
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* STEP: Input */}
      {step === 'input' && (
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
          <View style={styles.header}>
            <Text style={styles.title}>🚀 AI Planner</Text>
            <Text style={styles.subtitle}>
              Podaj zadania, a AI stworzy optymalny plan dnia
            </Text>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>📋 Twoje zadania</Text>
            
            {tasks.map((task, index) => (
              <View key={index} style={styles.taskRow}>
                <TextInput
                  style={styles.taskInput}
                  value={task}
                  onChangeText={(text) => updateTask(index, text)}
                  placeholder={`Zadanie ${index + 1}...`}
                  placeholderTextColor={theme.textSecondary}
                />
                {tasks.length > 1 && (
                  <TouchableOpacity
                    style={styles.removeButton}
                    onPress={() => removeTask(index)}
                  >
                    <Ionicons name="close-circle" size={24} color={theme.error} />
                  </TouchableOpacity>
                )}
              </View>
            ))}
            
            <TouchableOpacity style={styles.addButton} onPress={addTask}>
              <Ionicons name="add-circle-outline" size={24} color={theme.primary} />
              <Text style={styles.addButtonText}>Dodaj zadanie</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>⚙️ Preferencje</Text>
            <View style={styles.prefItem}>
              <Text style={styles.prefLabel}>Sen:</Text>
              <Text style={styles.prefValue}>{preferences.sleepSchedule}</Text>
            </View>
            <View style={styles.prefItem}>
              <Text style={styles.prefLabel}>Deep Work:</Text>
              <Text style={styles.prefValue}>{preferences.deepWorkWindows}</Text>
            </View>
            <Text style={styles.prefHint}>
              Możesz zmienić preferencje w Ustawieniach
            </Text>
          </View>

          <TouchableOpacity style={styles.generateButton} onPress={generatePlan}>
            <Ionicons name="sparkles" size={24} color={theme.text} />
            <Text style={styles.generateButtonText}>Wygeneruj plan</Text>
          </TouchableOpacity>
        </ScrollView>
      )}

      {/* STEP: Loading */}
      {step === 'loading' && (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={styles.loadingTitle}>Generuję plan...</Text>
          <Text style={styles.loadingSubtitle}>
            AI analizuje Twój kalendarz i tworzy optymalny harmonogram
          </Text>
        </View>
      )}

      {/* STEP: Review */}
      {step === 'review' && generatedPlan && (
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
          <View style={styles.header}>
            <Text style={styles.title}>📋 Wygenerowany plan</Text>
            <Text style={styles.subtitle}>
              Zaznacz wydarzenia, które chcesz dodać do kalendarza
            </Text>
          </View>

          {/* Reasoning */}
          {generatedPlan.reasoning && (
            <View style={styles.reasoningCard}>
              <Ionicons name="bulb-outline" size={20} color={theme.accent} />
              <Text style={styles.reasoningText}>{generatedPlan.reasoning}</Text>
            </View>
          )}

          {/* Events */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>
                Wydarzenia ({selectedEvents.size}/{generatedPlan.events.length})
              </Text>
              <TouchableOpacity
                onPress={() => {
                  if (selectedEvents.size === generatedPlan.events.length) {
                    setSelectedEvents(new Set());
                  } else {
                    setSelectedEvents(new Set(generatedPlan.events.map((_, i) => i)));
                  }
                }}
              >
                <Text style={styles.selectAllText}>
                  {selectedEvents.size === generatedPlan.events.length
                    ? 'Odznacz wszystkie'
                    : 'Zaznacz wszystkie'}
                </Text>
              </TouchableOpacity>
            </View>
            
            {generatedPlan.events.map(renderEventPreview)}
          </View>

          {/* Conflicts */}
          {generatedPlan.conflicts.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>⚠️ Konflikty</Text>
              {generatedPlan.conflicts.map((conflict, index) => (
                <View key={index} style={styles.conflictCard}>
                  <Text style={styles.conflictEvent}>{conflict.existing_event}</Text>
                  <Text style={styles.conflictTime}>{conflict.conflict_time}</Text>
                  <Text style={styles.conflictSuggestion}>{conflict.suggestion}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Actions */}
          <View style={styles.actionButtons}>
            <TouchableOpacity style={styles.cancelButton} onPress={reset}>
              <Text style={styles.cancelButtonText}>Anuluj</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.confirmButton, selectedEvents.size === 0 && styles.buttonDisabled]}
              onPress={executePlan}
              disabled={selectedEvents.size === 0}
            >
              <Ionicons name="checkmark-circle" size={24} color={theme.text} />
              <Text style={styles.confirmButtonText}>
                Zatwierdź ({selectedEvents.size})
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      )}

      {/* STEP: Executing */}
      {step === 'executing' && (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.success} />
          <Text style={styles.loadingTitle}>Dodaję do kalendarza...</Text>
          <Text style={styles.loadingSubtitle}>
            Tworzę wydarzenia w Google Calendar
          </Text>
        </View>
      )}

      {/* STEP: Done */}
      {step === 'done' && (
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
          <View style={styles.doneContainer}>
            <View style={styles.doneIcon}>
              <Ionicons name="checkmark-circle" size={80} color={theme.success} />
            </View>
            <Text style={styles.doneTitle}>Plan dodany! 🎉</Text>
            <Text style={styles.doneSubtitle}>
              Twoje wydarzenia zostały dodane do Google Calendar
            </Text>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Podsumowanie</Text>
            {executionResults.map((result, index) => (
              <Text key={index} style={styles.resultItem}>
                {result}
              </Text>
            ))}
          </View>

          <TouchableOpacity style={styles.newPlanButton} onPress={reset}>
            <Ionicons name="add-circle-outline" size={24} color={theme.text} />
            <Text style={styles.newPlanButtonText}>Stwórz nowy plan</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    color: theme.textSecondary,
    lineHeight: 22,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 12,
  },
  selectAllText: {
    fontSize: 14,
    color: theme.primary,
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  taskInput: {
    flex: 1,
    backgroundColor: theme.card,
    borderRadius: 12,
    padding: 16,
    color: theme.text,
    fontSize: 16,
  },
  removeButton: {
    padding: 4,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    backgroundColor: 'rgba(99, 102, 241, 0.1)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.primary,
    borderStyle: 'dashed',
    gap: 8,
  },
  addButtonText: {
    color: theme.primary,
    fontSize: 16,
    fontWeight: '500',
  },
  prefItem: {
    flexDirection: 'row',
    backgroundColor: theme.card,
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  prefLabel: {
    color: theme.textSecondary,
    fontSize: 14,
    width: 100,
  },
  prefValue: {
    color: theme.text,
    fontSize: 14,
    flex: 1,
  },
  prefHint: {
    color: theme.textSecondary,
    fontSize: 12,
    marginTop: 8,
    fontStyle: 'italic',
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.primary,
    padding: 18,
    borderRadius: 16,
    gap: 12,
    marginTop: 16,
  },
  generateButtonText: {
    color: theme.text,
    fontSize: 18,
    fontWeight: '600',
  },
  centerContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  loadingTitle: {
    fontSize: 22,
    fontWeight: '600',
    color: theme.text,
    marginTop: 24,
  },
  loadingSubtitle: {
    fontSize: 15,
    color: theme.textSecondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
  },
  reasoningCard: {
    flexDirection: 'row',
    backgroundColor: 'rgba(34, 211, 238, 0.1)',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
    gap: 12,
    alignItems: 'flex-start',
  },
  reasoningText: {
    flex: 1,
    color: theme.accent,
    fontSize: 14,
    lineHeight: 20,
  },
  eventPreview: {
    flexDirection: 'row',
    backgroundColor: theme.card,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  eventPreviewSelected: {
    borderColor: theme.success,
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
  },
  eventCheckbox: {
    marginRight: 12,
    paddingTop: 2,
  },
  eventPreviewContent: {
    flex: 1,
  },
  eventPreviewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 6,
  },
  updateBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    gap: 4,
  },
  updateBadgeText: {
    color: theme.warning,
    fontSize: 11,
    fontWeight: '600',
  },
  eventPreviewTitle: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  eventPreviewTime: {
    color: theme.accent,
    fontSize: 13,
    marginBottom: 4,
  },
  eventPreviewDesc: {
    color: theme.textSecondary,
    fontSize: 13,
    lineHeight: 18,
  },
  eventPreviewReason: {
    color: theme.warning,
    fontSize: 12,
    marginTop: 6,
    fontStyle: 'italic',
  },
  conflictCard: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: theme.error,
  },
  conflictEvent: {
    color: theme.error,
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 4,
  },
  conflictTime: {
    color: theme.textSecondary,
    fontSize: 13,
    marginBottom: 8,
  },
  conflictSuggestion: {
    color: theme.text,
    fontSize: 13,
    lineHeight: 18,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  cancelButton: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    backgroundColor: theme.card,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: theme.textSecondary,
    fontSize: 16,
    fontWeight: '600',
  },
  confirmButton: {
    flex: 2,
    flexDirection: 'row',
    padding: 16,
    borderRadius: 12,
    backgroundColor: theme.success,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  confirmButtonText: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  doneContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  doneIcon: {
    marginBottom: 16,
  },
  doneTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 8,
  },
  doneSubtitle: {
    fontSize: 15,
    color: theme.textSecondary,
    textAlign: 'center',
  },
  resultItem: {
    color: theme.text,
    fontSize: 14,
    lineHeight: 24,
    paddingVertical: 4,
  },
  newPlanButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.primary,
    padding: 18,
    borderRadius: 16,
    gap: 12,
    marginTop: 16,
  },
  newPlanButtonText: {
    color: theme.text,
    fontSize: 18,
    fontWeight: '600',
  },
});
