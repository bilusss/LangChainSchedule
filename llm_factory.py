"""
Fabryka LLM - tworzy odpowiedni model na podstawie wybranego providera
"""

import os
import getpass
from typing import Any

from config import ModelProvider, LOCAL_URLS


def create_llm(provider: ModelProvider, model_name: str, temperature: float = 0.3) -> Any:
    """
    Tworzy instancję LLM dla wybranego providera.
    
    Args:
        provider: Provider modelu (Gemini, Ollama, LM Studio, OpenAI)
        model_name: Nazwa modelu
        temperature: Temperatura generowania (0.0 - 1.0)
    
    Returns:
        Instancja LLM kompatybilna z LangChain
    """
    
    if provider == ModelProvider.GEMINI:
        return _create_gemini(model_name, temperature)
    
    elif provider == ModelProvider.OLLAMA:
        return _create_ollama(model_name, temperature)
    
    elif provider == ModelProvider.LMSTUDIO:
        return _create_lmstudio(model_name, temperature)
    
    elif provider == ModelProvider.OPENAI:
        return _create_openai(model_name, temperature)
    
    else:
        raise ValueError(f"Nieznany provider: {provider}")


def _create_gemini(model_name: str, temperature: float):
    """Tworzy model Gemini (Google)"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Sprawdź klucz API
    if "GOOGLE_API_KEY" not in os.environ:
        llm_key = os.getenv("GOOGLE_API_KEY_LLM")
        if llm_key:
            os.environ["GOOGLE_API_KEY"] = llm_key
            print("✅ Załadowano GOOGLE_API_KEY_LLM dla Gemini")
        else:
            raw_key = getpass.getpass("Podaj Google API Key: ")
            os.environ["GOOGLE_API_KEY"] = raw_key.strip()
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=2,
    )


def _create_ollama(model_name: str, temperature: float):
    """Tworzy model Ollama (lokalny)"""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        print("❌ Brak pakietu langchain-ollama. Instaluję...")
        import subprocess
        subprocess.check_call(["pip", "install", "langchain-ollama"])
        from langchain_ollama import ChatOllama
    
    base_url = LOCAL_URLS[ModelProvider.OLLAMA]
    
    print(f"🔗 Łączę z Ollama: {base_url}")
    print(f"📦 Model: {model_name}")
    
    return ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=temperature,
    )


def _create_lmstudio(model_name: str, temperature: float):
    """Tworzy model LM Studio (lokalny, OpenAI-kompatybilny)"""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("❌ Brak pakietu langchain-openai. Instaluję...")
        import subprocess
        subprocess.check_call(["pip", "install", "langchain-openai"])
        from langchain_openai import ChatOpenAI
    
    base_url = LOCAL_URLS[ModelProvider.LMSTUDIO]
    
    print(f"🔗 Łączę z LM Studio: {base_url}")
    print(f"📦 Model: {model_name}")
    
    # LM Studio nie wymaga klucza API, ale LangChain go wymaga
    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key="lm-studio",  # Dummy key
        temperature=temperature,
    )


def _create_openai(model_name: str, temperature: float):
    """Tworzy model OpenAI"""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("❌ Brak pakietu langchain-openai. Instaluję...")
        import subprocess
        subprocess.check_call(["pip", "install", "langchain-openai"])
        from langchain_openai import ChatOpenAI
    
    # Sprawdź klucz API
    if "OPENAI_API_KEY" not in os.environ:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raw_key = getpass.getpass("Podaj OpenAI API Key: ")
            os.environ["OPENAI_API_KEY"] = raw_key.strip()
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
    )
