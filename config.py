"""
Konfiguracja projektu - wybór modelu LLM i ustawienia
"""

import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class ModelProvider(Enum):
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OPENAI = "openai"


# Domyślne modele dla każdego providera
DEFAULT_MODELS = {
    ModelProvider.GEMINI: "gemini-2.5-flash-lite",
    ModelProvider.OLLAMA: "llama3.1:8b",  # Obsługuje function calling
    ModelProvider.LMSTUDIO: "qwen2.5-7b-instruct",  # Lub inny załadowany model
    ModelProvider.OPENAI: "gpt-4o-mini",
}

# URL dla lokalnych providerów
LOCAL_URLS = {
    ModelProvider.OLLAMA: "http://localhost:11434",
    ModelProvider.LMSTUDIO: "http://localhost:1234/v1",
}

# Modele Ollama wspierające function calling
OLLAMA_TOOL_MODELS = [
    "llama3.1",
    "llama3.2",
    "llama3.3",
    "mistral",
    "mistral-nemo",
    "qwen2.5",
    "qwen2.5-coder",
    "mixtral",
    "command-r",
    "command-r-plus",
]


def select_provider_interactive() -> tuple[ModelProvider, str]:
    """
    Pozwala użytkownikowi wybrać provider modelu w terminalu.
    
    Returns:
        Tuple (provider, model_name)
    """
    print("\n" + "=" * 50)
    print("🤖 WYBÓR MODELU LLM")
    print("=" * 50)
    print("\nDostępne opcje:")
    print("  1. Gemini API (Google) - wymaga GOOGLE_API_KEY")
    print("  2. Ollama (lokalny) - wymaga uruchomionego Ollama")
    print("  3. LM Studio (lokalny) - wymaga uruchomionego LM Studio")
    print("  4. OpenAI API - wymaga OPENAI_API_KEY")
    print("=" * 50)
    
    while True:
        try:
            choice = input("\nWybierz opcję (1-4) [domyślnie 1]: ").strip()
            
            if not choice or choice == "1":
                provider = ModelProvider.GEMINI
                break
            elif choice == "2":
                provider = ModelProvider.OLLAMA
                break
            elif choice == "3":
                provider = ModelProvider.LMSTUDIO
                break
            elif choice == "4":
                provider = ModelProvider.OPENAI
                break
            else:
                print("❌ Nieprawidłowy wybór. Wpisz 1, 2, 3 lub 4.")
        except EOFError:
            provider = ModelProvider.GEMINI
            break
    
    default_model = DEFAULT_MODELS[provider]
    
    # Zapytaj o nazwę modelu
    model_input = input(f"Nazwa modelu [{default_model}]: ").strip()
    model_name = model_input if model_input else default_model
    
    # Ostrzeżenie dla Ollama jeśli model może nie wspierać tools
    if provider == ModelProvider.OLLAMA:
        model_base = model_name.split(":")[0]
        if model_base not in OLLAMA_TOOL_MODELS:
            print(f"\n⚠️  UWAGA: Model '{model_name}' może nie wspierać function calling.")
            print("    Zalecane modele z obsługą tools: " + ", ".join(OLLAMA_TOOL_MODELS[:5]))
    
    print(f"\n✅ Wybrano: {provider.value} / {model_name}\n")
    
    return provider, model_name


def get_provider_from_env() -> tuple[ModelProvider, str]:
    """
    Pobiera provider z zmiennych środowiskowych (dla trybu nieinteraktywnego).
    """
    provider_str = os.getenv("LLM_PROVIDER", "gemini").lower()
    model_name = os.getenv("LLM_MODEL", "")
    
    provider_map = {
        "gemini": ModelProvider.GEMINI,
        "ollama": ModelProvider.OLLAMA,
        "lmstudio": ModelProvider.LMSTUDIO,
        "openai": ModelProvider.OPENAI,
    }
    
    provider = provider_map.get(provider_str, ModelProvider.GEMINI)
    
    if not model_name:
        model_name = DEFAULT_MODELS[provider]
    
    return provider, model_name
