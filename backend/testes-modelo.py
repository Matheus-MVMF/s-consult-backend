import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

chave = os.getenv("GOOGLE_API_KEY")
print(f"Testando chave: {chave[:5]}...{chave[-5:]}")

genai.configure(api_key=chave)

print("\nModelos disponíveis para você:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Erro ao listar: {e}")