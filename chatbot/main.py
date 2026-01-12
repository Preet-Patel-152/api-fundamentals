from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import List, Dict, Any


# ----- Config & Client Setup -----
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Fail fast if key is missing
    raise RuntimeError(
        "OPENAI_API_KEY is not set. "
        "Check your .env file or environment variables."
    )

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="AI Chat & Resume Grader",
    version="0.1.0",
    description="Simple FastAPI backend for chat and resume-job matching",
)


# ----- Pydantic Models -----
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class MatchRequest(BaseModel):
    job_description: str   # job post text
    resume_text: str       # PDF already converted to plain text


class GradeResponse(BaseModel):
    evaluation: str


# ----- Helper: generic OpenAI call -----
def call_chat_model(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4.1-mini",
    temperature: float = 0.2,
) -> str:
    """
    Small wrapper to call OpenAI Chat Completions and handle errors consistently.
    """
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
    except Exception as e:
        # Bubble this up as an HTTP error so FastAPI returns 500
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

    msg = completion.choices[0].message.content
    if msg is None:
        raise HTTPException(
            status_code=500,
            detail="OpenAI returned an empty response."
        )
    return msg


# ----- Chatbot Logic -----
def get_bot_reply(user_message: str) -> str:
    # Keep original case, just use a quick check for greetings
    lower_msg = user_message.lower()

    if any(greeting in lower_msg for greeting in ["hello", "hi", "hey"]):
        return "Hello! How can I assist you today?"

    # Use the model for anything else
    messages = [
        {
            "role": "system",
            "content": (
                "You are a top-level advisor. "
                "Give clear, helpful, and concise answers."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]
    return call_chat_model(messages)


# ----- Resume Grading Logic -----
RESUME_SYSTEM_PROMPT = """
You are an expert recruiter and resume reviewer.

Given a job description and a candidate resume, evaluate how well the resume matches the job.

Your response MUST include:
- A match score from 0 to 100 (label it clearly, e.g. "Match Score: 82/100")
- 3–5 bullet points on key strengths
- 3–5 bullet points on gaps or missing skills
- Concrete suggestions to improve the resume for this specific job
"""


def grade_resume_against_job(job_description: str, resume_text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": RESUME_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": (
                f"JOB DESCRIPTION:\n{job_description}\n\n"
                f"RESUME:\n{resume_text}"
            ),
        },
    ]
    return call_chat_model(messages)


# ----- FastAPI Routes -----
@app.post("/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Simple chat endpoint:
    Input: {"message": "..."}
    Output: {"reply": "..."}
    """
    reply = get_bot_reply(request.message)
    return ChatResponse(reply=reply)


@app.post("/grade_resume/", response_model=GradeResponse)
async def grade_resume(request: MatchRequest) -> GradeResponse:
    """
    Expects JSON like:
    {
      "job_description": "...",
      "resume_text": "..."   // PDF already converted to text
    }
    """
    evaluation = grade_resume_against_job(
        job_description=request.job_description,
        resume_text=request.resume_text,
    )
    return GradeResponse(evaluation=evaluation)
