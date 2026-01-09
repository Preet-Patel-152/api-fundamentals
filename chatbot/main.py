from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
app = FastAPI()
client = OpenAI(api_key=api_key)


class ChatRequest(BaseModel):
    message: str


def get_bot_reply(user_message):
    user_message = user_message.lower()
    if "hello" in user_message or "hi" in user_message:
        return "Hello! How can I assist you today?"
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_message}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"


@app.post("/chat/")
def chat(request: ChatRequest):
    reply = get_bot_reply(request.message)
    return ({"reply": reply})
