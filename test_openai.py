from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")
print("API key loaded:", bool(api_key))

client = OpenAI(api_key=api_key)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello"}],
)

print(resp.choices[0].message.content)
