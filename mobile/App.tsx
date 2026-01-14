import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StyleSheet } from 'react-native';

// Screens
import ChatScreen from './src/screens/ChatScreen';
import CalendarScreen from './src/screens/CalendarScreen';
import PlannerScreen from './src/screens/PlannerScreen';
import SettingsScreen from './src/screens/SettingsScreen';

// Context
import { AppProvider } from './src/context/AppContext';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

// Theme colors
const theme = {
  primary: '#6366f1',
  background: '#0f0f23',
  card: '#1a1a2e',
  text: '#ffffff',
  textSecondary: '#a0a0b0',
  accent: '#22d3ee',
  success: '#10b981',
  error: '#ef4444',
};

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap;

          if (route.name === 'Chat') {
            iconName = focused ? 'chatbubbles' : 'chatbubbles-outline';
          } else if (route.name === 'Kalendarz') {
            iconName = focused ? 'calendar' : 'calendar-outline';
          } else if (route.name === 'Planner') {
            iconName = focused ? 'rocket' : 'rocket-outline';
          } else if (route.name === 'Ustawienia') {
            iconName = focused ? 'settings' : 'settings-outline';
          } else {
            iconName = 'help-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textSecondary,
        tabBarStyle: {
          backgroundColor: theme.card,
          borderTopColor: '#2a2a4e',
          borderTopWidth: 1,
          paddingBottom: 5,
          height: 85,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
        headerStyle: {
          backgroundColor: theme.background,
        },
        headerTintColor: theme.text,
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      })}
    >
      <Tab.Screen 
        name="Chat" 
        component={ChatScreen}
        options={{
          title: 'Asystent AI',
          headerTitle: '🤖 Asystent AI',
        }}
      />
      <Tab.Screen 
        name="Kalendarz" 
        component={CalendarScreen}
        options={{
          headerTitle: '📅 Kalendarz',
        }}
      />
      <Tab.Screen 
        name="Planner" 
        component={PlannerScreen}
        options={{
          headerTitle: '🚀 AI Planner',
        }}
      />
      <Tab.Screen 
        name="Ustawienia" 
        component={SettingsScreen}
        options={{
          headerTitle: '⚙️ Ustawienia',
        }}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={styles.container}>
      <AppProvider>
        <NavigationContainer
          theme={{
            dark: true,
            colors: {
              primary: theme.primary,
              background: theme.background,
              card: theme.card,
              text: theme.text,
              border: '#2a2a4e',
              notification: theme.accent,
            },
          }}
        >
          <StatusBar style="light" />
          <MainTabs />
        </NavigationContainer>
      </AppProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
});
