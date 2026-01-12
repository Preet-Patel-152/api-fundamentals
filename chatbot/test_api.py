from openai import OpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the same folder as this file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

print("CWD:", os.getcwd())
print("Loaded key:", os.getenv("OPENAI_API_KEY"))  # debug

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, is the API working?"}]
)

print(response.choices[0].message.content)
