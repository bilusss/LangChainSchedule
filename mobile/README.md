# Calendar AI Mobile

Aplikacja React Native do zarządzania kalendarzem z asystentem AI i rozpoznawaniem mowy.

## 🚀 Szybki start (iPhone z Expo Go)

### 1. Uruchom backend Python

```bash
# W głównym folderze projektu
cd /Users/bilus/PycharmProjects/LangChainSchedule

# Zainstaluj dodatkowe zależności dla API
pip install fastapi uvicorn

# Uruchom API
python api.py
```

Backend powinien wystartować na `http://0.0.0.0:8000`

### 2. Znajdź IP swojego komputera

```bash
# macOS
ipconfig getifaddr en0
```

Zapisz IP (np. `192.168.1.100`) - będziesz go potrzebować w aplikacji.

### 3. Zainstaluj Expo Go na iPhone

Pobierz **Expo Go** z App Store na swoim iPhone.

### 4. Uruchom aplikację mobilną

```bash
# W folderze mobile
cd mobile

# Zainstaluj zależności
npm install

# Uruchom Expo
npx expo start
```

### 5. Skanuj QR kod

Po uruchomieniu `npx expo start`:
- Otwórz aparat iPhone
- Zeskanuj wyświetlony QR kod
- Aplikacja otworzy się w Expo Go

### 6. Skonfiguruj połączenie

W aplikacji przejdź do **Ustawienia** i zmień adres API na:
```
http://TWOJE_IP:8000
```
np. `http://192.168.1.100:8000`

## 📱 Funkcje aplikacji

### 🤖 Chat z AI
- Rozmawiaj z asystentem po polsku
- **Przytrzymaj przycisk mikrofonu** aby mówić
- Asystent ma dostęp do Twojego Google Calendar

### 📅 Kalendarz
- Przeglądaj wydarzenia z Google Calendar
- Filtruj po 7/14/30 dni
- Pull-to-refresh

### 🚀 AI Planner
- Podaj listę zadań
- AI wygeneruje optymalny plan dnia
- Zatwierdź wybrane wydarzenia
- Automatycznie dodaje do Google Calendar

### ⚙️ Ustawienia
- Konfiguracja adresu API
- Preferencje planowania (sen, deep work, nawyki)
- Test połączenia z serwerem

## 🎤 Speech-to-Text

Aplikacja używa **Whisper Large V3** przez GROQ API do rozpoznawania mowy.
- Najlepsza obsługa języka polskiego
- Szybka transkrypcja (cloud-based)
- Przytrzymaj przycisk mikrofonu aby nagrać

## 🔧 Wymagania

### Backend
- Python 3.10+
- Klucze API w `.env`:
  - `GROQ_API_KEY` - dla planera i speech-to-text
  - `GOOGLE_API_KEY_LLM` - dla Gemini (chat)
  - Google Calendar OAuth2 (`credentials.json`)

### Mobile
- Node.js 18+
- Expo Go na iPhone
- iPhone i komputer w tej samej sieci WiFi

## 📂 Struktura projektu

```
LangChainSchedule/
├── api.py                 # FastAPI backend
├── main.py                # Oryginalny CLI
├── groq_planner.py        # GROQ Planner
├── tools/
│   └── google_calendar.py # Google Calendar tools
├── mobile/
│   ├── App.tsx            # Główny komponent
│   ├── src/
│   │   ├── screens/
│   │   │   ├── ChatScreen.tsx
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── PlannerScreen.tsx
│   │   │   └── SettingsScreen.tsx
│   │   ├── services/
│   │   │   ├── api.ts     # HTTP client
│   │   │   └── audio.ts   # Audio recording
│   │   └── context/
│   │       └── AppContext.tsx
│   ├── package.json
│   └── app.json
```

## 🐛 Rozwiązywanie problemów

### "Network Error" w aplikacji
1. Upewnij się, że backend działa (`python api.py`)
2. Sprawdź czy użyłeś prawidłowego IP (nie `localhost`)
3. Upewnij się, że telefon i komputer są w tej samej sieci WiFi
4. Sprawdź czy port 8000 nie jest zablokowany przez firewall

### Mikrofon nie działa
1. Przy pierwszym użyciu aplikacja poprosi o uprawnienia
2. Jeśli odmówiłeś, włącz uprawnienia w ustawieniach iPhone

### Błąd transkrypcji
1. Sprawdź czy masz ustawiony `GROQ_API_KEY` w `.env`
2. Upewnij się, że nagranie trwa co najmniej 1 sekundę

## 🔐 Bezpieczeństwo

⚠️ **Uwaga**: Ta aplikacja jest przeznaczona do użytku lokalnego/deweloperskiego.
Przed wdrożeniem produkcyjnym:
- Dodaj autentykację do API
- Użyj HTTPS
- Ogranicz CORS origins
