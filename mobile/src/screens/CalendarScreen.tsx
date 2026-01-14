/**
 * Calendar Screen - widok wydarzeń z kalendarza
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { format, parseISO, isToday, isTomorrow, isThisWeek } from 'date-fns';
import { pl } from 'date-fns/locale';

import { useApp } from '../context/AppContext';
import apiService from '../services/api';

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

// Typ wydarzenia
interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  location?: string;
  description?: string;
}

export default function CalendarScreen() {
  const { isConnected } = useApp();
  
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [daysAhead, setDaysAhead] = useState(7);
  const [rawData, setRawData] = useState<string>('');

  // Pobierz wydarzenia
  const fetchEvents = useCallback(async (refresh = false) => {
    if (refresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const result = await apiService.getCalendarEvents(daysAhead, 50);
      setRawData(result);
      
      // Parsuj wydarzenia z tekstu (format z API)
      const parsedEvents = parseEventsFromText(result);
      setEvents(parsedEvents);
      
      if (refresh) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
    } catch (error) {
      console.error('Error fetching events:', error);
      Alert.alert('Błąd', 'Nie udało się pobrać wydarzeń z kalendarza');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [daysAhead]);

  // Parsowanie wydarzeń z tekstu API
  const parseEventsFromText = (text: string): CalendarEvent[] => {
    const events: CalendarEvent[] = [];
    const lines = text.split('\n');
    
    let currentEvent: Partial<CalendarEvent> = {};
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      // Nowe wydarzenie
      if (trimmed.startsWith('• [')) {
        if (currentEvent.id) {
          events.push(currentEvent as CalendarEvent);
        }
        
        // Parsuj ID i nazwę
        const idMatch = trimmed.match(/\[([^\]]+)\]/);
        const nameMatch = trimmed.match(/\] (.+)$/);
        
        currentEvent = {
          id: idMatch?.[1] || '',
          summary: nameMatch?.[1] || 'Bez tytułu',
        };
      }
      // Start
      else if (trimmed.startsWith('Start:')) {
        currentEvent.start = trimmed.replace('Start:', '').trim();
      }
      // Koniec
      else if (trimmed.startsWith('Koniec:')) {
        currentEvent.end = trimmed.replace('Koniec:', '').trim();
      }
      // Miejsce
      else if (trimmed.startsWith('Miejsce:')) {
        currentEvent.location = trimmed.replace('Miejsce:', '').trim();
      }
    }
    
    // Dodaj ostatnie wydarzenie
    if (currentEvent.id) {
      events.push(currentEvent as CalendarEvent);
    }
    
    return events;
  };

  // Pobierz wydarzenia przy starcie
  useEffect(() => {
    fetchEvents();
  }, [daysAhead]);

  // Formatowanie daty
  const formatEventDate = (dateStr: string): { date: string; time: string; badge?: string } => {
    try {
      const date = parseISO(dateStr);
      
      let badge: string | undefined;
      if (isToday(date)) {
        badge = 'Dziś';
      } else if (isTomorrow(date)) {
        badge = 'Jutro';
      }
      
      return {
        date: format(date, 'EEEE, d MMMM', { locale: pl }),
        time: format(date, 'HH:mm'),
        badge,
      };
    } catch {
      return { date: dateStr, time: '' };
    }
  };

  // Grupowanie wydarzeń po dacie
  const groupEventsByDate = (events: CalendarEvent[]): Map<string, CalendarEvent[]> => {
    const groups = new Map<string, CalendarEvent[]>();
    
    for (const event of events) {
      try {
        const date = parseISO(event.start);
        const dateKey = format(date, 'yyyy-MM-dd');
        
        if (!groups.has(dateKey)) {
          groups.set(dateKey, []);
        }
        groups.get(dateKey)?.push(event);
      } catch {
        // Skip invalid dates
      }
    }
    
    return groups;
  };

  // Render pojedynczego wydarzenia
  const renderEvent = (event: CalendarEvent) => {
    const startInfo = formatEventDate(event.start);
    const endInfo = formatEventDate(event.end);

    return (
      <View style={styles.eventCard} key={event.id}>
        <View style={styles.eventTimeContainer}>
          <Text style={styles.eventTime}>{startInfo.time}</Text>
          <View style={styles.timeLine} />
          <Text style={styles.eventTimeEnd}>{endInfo.time}</Text>
        </View>
        
        <View style={styles.eventContent}>
          <Text style={styles.eventTitle}>{event.summary}</Text>
          
          {event.location && (
            <View style={styles.eventDetail}>
              <Ionicons name="location-outline" size={14} color={theme.textSecondary} />
              <Text style={styles.eventDetailText}>{event.location}</Text>
            </View>
          )}
        </View>
        
        {startInfo.badge && (
          <View style={[
            styles.badge,
            startInfo.badge === 'Dziś' ? styles.badgeToday : styles.badgeTomorrow
          ]}>
            <Text style={styles.badgeText}>{startInfo.badge}</Text>
          </View>
        )}
      </View>
    );
  };

  // Render grupy wydarzeń
  const renderEventGroup = ({ item }: { item: [string, CalendarEvent[]] }) => {
    const [dateKey, events] = item;
    const firstEvent = events[0];
    const dateInfo = formatEventDate(firstEvent.start);

    return (
      <View style={styles.dateGroup}>
        <View style={styles.dateHeader}>
          <Text style={styles.dateText}>{dateInfo.date}</Text>
          <Text style={styles.eventCount}>{events.length} wydarzeń</Text>
        </View>
        {events.map(renderEvent)}
      </View>
    );
  };

  const groupedEvents = Array.from(groupEventsByDate(events).entries());

  return (
    <View style={styles.container}>
      {/* Filtry */}
      <View style={styles.filterContainer}>
        {[7, 14, 30].map((days) => (
          <TouchableOpacity
            key={days}
            style={[styles.filterButton, daysAhead === days && styles.filterButtonActive]}
            onPress={() => setDaysAhead(days)}
          >
            <Text style={[styles.filterText, daysAhead === days && styles.filterTextActive]}>
              {days} dni
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Lista wydarzeń */}
      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={styles.loadingText}>Ładowanie wydarzeń...</Text>
        </View>
      ) : events.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Ionicons name="calendar-outline" size={64} color={theme.textSecondary} />
          <Text style={styles.emptyText}>Brak wydarzeń</Text>
          <Text style={styles.emptySubtext}>
            Twój kalendarz jest pusty na najbliższe {daysAhead} dni
          </Text>
        </View>
      ) : (
        <FlatList
          data={groupedEvents}
          renderItem={renderEventGroup}
          keyExtractor={([dateKey]) => dateKey}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={() => fetchEvents(true)}
              tintColor={theme.primary}
              colors={[theme.primary]}
            />
          }
        />
      )}

      {/* FAB - dodaj wydarzenie */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          Alert.alert(
            'Dodaj wydarzenie',
            'Użyj chatu AI, żeby dodać wydarzenie naturalnym językiem!\n\nNapisz np. "Dodaj spotkanie z Anią jutro o 15:00"',
            [{ text: 'OK' }]
          );
        }}
      >
        <Ionicons name="add" size={28} color={theme.text} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a4e',
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: theme.card,
  },
  filterButtonActive: {
    backgroundColor: theme.primary,
  },
  filterText: {
    color: theme.textSecondary,
    fontSize: 14,
    fontWeight: '500',
  },
  filterTextActive: {
    color: theme.text,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  loadingText: {
    color: theme.textSecondary,
    fontSize: 16,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 12,
  },
  emptyText: {
    color: theme.text,
    fontSize: 20,
    fontWeight: '600',
  },
  emptySubtext: {
    color: theme.textSecondary,
    fontSize: 15,
    textAlign: 'center',
  },
  listContent: {
    padding: 16,
    paddingBottom: 100,
  },
  dateGroup: {
    marginBottom: 24,
  },
  dateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dateText: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  eventCount: {
    color: theme.textSecondary,
    fontSize: 13,
  },
  eventCard: {
    flexDirection: 'row',
    backgroundColor: theme.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
  },
  eventTimeContainer: {
    alignItems: 'center',
    marginRight: 16,
    width: 50,
  },
  eventTime: {
    color: theme.accent,
    fontSize: 15,
    fontWeight: '600',
  },
  timeLine: {
    width: 2,
    height: 20,
    backgroundColor: '#3a3a5e',
    marginVertical: 4,
  },
  eventTimeEnd: {
    color: theme.textSecondary,
    fontSize: 13,
  },
  eventContent: {
    flex: 1,
  },
  eventTitle: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 6,
  },
  eventDetail: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  eventDetailText: {
    color: theme.textSecondary,
    fontSize: 13,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  badgeToday: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
  },
  badgeTomorrow: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: theme.success,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: theme.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: theme.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
});
