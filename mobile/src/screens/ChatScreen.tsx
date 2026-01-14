/**
 * Chat Screen - główny ekran z asystentem AI
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

import { useApp } from '../context/AppContext';
import apiService from '../services/api';
import audioService from '../services/audio';

// Typy
interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

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
  userBubble: '#6366f1',
  aiBubble: '#2a2a4e',
};

export default function ChatScreen() {
  const { conversationId, setConversationId, isConnected } = useApp();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  
  const flatListRef = useRef<FlatList>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const recordingInterval = useRef<NodeJS.Timeout | null>(null);

  // Animacja pulsowania podczas nagrywania
  useEffect(() => {
    if (isRecording) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 500,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      
      // Timer nagrywania
      recordingInterval.current = setInterval(() => {
        setRecordingDuration(audioService.getRecordingDuration());
      }, 100);
      
      return () => {
        pulse.stop();
        if (recordingInterval.current) {
          clearInterval(recordingInterval.current);
        }
      };
    }
  }, [isRecording]);

  // Wiadomość powitalna
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        text: '👋 Cześć! Jestem Twoim asystentem kalendarza. Możesz mnie zapytać o wydarzenia, poprosić o zaplanowanie dnia, lub dodać nowe spotkania.\n\n🎤 Możesz też użyć przycisku mikrofonu, żeby mówić po polsku!',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, []);

  // Wysłanie wiadomości
  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: text.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await apiService.sendMessage(text, conversationId || undefined);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      const aiMessage: Message = {
        id: Date.now().toString() + '_ai',
        text: response.response,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (error) {
      const errorMessage: Message = {
        id: Date.now().toString() + '_error',
        text: '❌ Nie udało się połączyć z serwerem. Sprawdź ustawienia API.',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    } finally {
      setIsLoading(false);
    }
  };

  // Rozpoczęcie nagrywania
  const startRecording = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    
    const started = await audioService.startRecording();
    if (started) {
      setIsRecording(true);
      setRecordingDuration(0);
    } else {
      const errorMessage: Message = {
        id: Date.now().toString() + '_error',
        text: '❌ Nie udało się rozpocząć nagrywania. Sprawdź uprawnienia mikrofonu.',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // Zakończenie nagrywania
  const stopRecording = async () => {
    if (!audioService.getIsRecording()) {
      return; // Nie ma aktywnego nagrywania
    }
    
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setIsRecording(false);
    
    if (recordingInterval.current) {
      clearInterval(recordingInterval.current);
    }

    const result = await audioService.stopRecording();
    
    if (result.success && result.text) {
      setInputText(result.text);
      // Automatycznie wyślij
      sendMessage(result.text);
    } else if (!result.success) {
      const errorMessage: Message = {
        id: Date.now().toString() + '_error',
        text: `❌ Błąd transkrypcji: ${result.error || 'Nieznany błąd'}`,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // Toggle nagrywania (kliknięcie zamiast przytrzymania)
  const toggleRecording = async () => {
    if (isRecording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  // Anulowanie nagrywania
  const cancelRecording = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setIsRecording(false);
    
    if (recordingInterval.current) {
      clearInterval(recordingInterval.current);
    }
    
    await audioService.cancelRecording();
  };

  // Formatowanie czasu nagrywania
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Render pojedynczej wiadomości
  const renderMessage = ({ item }: { item: Message }) => (
    <View
      style={[
        styles.messageBubble,
        item.isUser ? styles.userBubble : styles.aiBubble,
      ]}
    >
      {!item.isUser && (
        <Text style={styles.aiLabel}>🤖 Asystent</Text>
      )}
      <Text style={styles.messageText}>{item.text}</Text>
      <Text style={styles.timestamp}>
        {item.timestamp.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}
      </Text>
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={90}
    >
      {/* Status połączenia */}
      {!isConnected && (
        <View style={styles.connectionWarning}>
          <Ionicons name="cloud-offline" size={16} color={theme.error} />
          <Text style={styles.connectionWarningText}>
            Brak połączenia z serwerem
          </Text>
        </View>
      )}

      {/* Lista wiadomości */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
        onLayout={() => flatListRef.current?.scrollToEnd()}
      />

      {/* Indicator ładowania */}
      {isLoading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color={theme.primary} />
          <Text style={styles.loadingText}>Myślę...</Text>
        </View>
      )}

      {/* Nagrywanie */}
      {isRecording && (
        <View style={styles.recordingContainer}>
          <Animated.View style={[styles.recordingPulse, { transform: [{ scale: pulseAnim }] }]}>
            <Ionicons name="mic" size={24} color={theme.error} />
          </Animated.View>
          <Text style={styles.recordingText}>
            Nagrywam... {formatDuration(recordingDuration)}
          </Text>
          <TouchableOpacity onPress={cancelRecording} style={styles.cancelButton}>
            <Ionicons name="close" size={20} color={theme.textSecondary} />
          </TouchableOpacity>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Napisz wiadomość..."
          placeholderTextColor={theme.textSecondary}
          multiline
          maxLength={2000}
          editable={!isRecording}
        />

        {/* Przycisk mikrofonu - kliknij aby rozpocząć/zakończyć nagrywanie */}
        <TouchableOpacity
          style={[styles.micButton, isRecording && styles.micButtonRecording]}
          onPress={toggleRecording}
          disabled={isLoading}
        >
          <Ionicons
            name={isRecording ? 'stop' : 'mic-outline'}
            size={24}
            color={isRecording ? theme.error : theme.text}
          />
        </TouchableOpacity>

        {/* Przycisk wysyłania */}
        <TouchableOpacity
          style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
          onPress={() => sendMessage(inputText)}
          disabled={!inputText.trim() || isLoading}
        >
          <Ionicons name="send" size={20} color={theme.text} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  connectionWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    paddingVertical: 8,
    gap: 8,
  },
  connectionWarningText: {
    color: theme.error,
    fontSize: 13,
  },
  messagesList: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  messageBubble: {
    maxWidth: '85%',
    padding: 12,
    borderRadius: 16,
    marginVertical: 4,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: theme.userBubble,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    alignSelf: 'flex-start',
    backgroundColor: theme.aiBubble,
    borderBottomLeftRadius: 4,
  },
  aiLabel: {
    fontSize: 11,
    color: theme.accent,
    marginBottom: 4,
    fontWeight: '600',
  },
  messageText: {
    color: theme.text,
    fontSize: 15,
    lineHeight: 22,
  },
  timestamp: {
    fontSize: 10,
    color: theme.textSecondary,
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    gap: 8,
  },
  loadingText: {
    color: theme.textSecondary,
    fontSize: 14,
  },
  recordingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    paddingVertical: 12,
    gap: 12,
  },
  recordingPulse: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
  },
  recordingText: {
    color: theme.error,
    fontSize: 15,
    fontWeight: '500',
  },
  cancelButton: {
    padding: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#2a2a4e',
    backgroundColor: theme.card,
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: '#2a2a4e',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: theme.text,
    fontSize: 15,
    maxHeight: 100,
  },
  micButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#2a2a4e',
    alignItems: 'center',
    justifyContent: 'center',
  },
  micButtonRecording: {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: theme.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#3a3a5e',
    opacity: 0.5,
  },
});
