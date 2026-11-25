import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
modelo = os.getenv("GEMINI_MODEL")

resposta = client.models.generate_content(
    model=modelo,
    contents="Explique em uma frase o que é uma cobrança recorrente.",
)
print(f"Modelo: {modelo}")
print(resposta.text)