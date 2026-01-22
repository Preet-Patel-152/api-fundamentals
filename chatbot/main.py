import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
from pathlib import Path
from io import BytesIO
import os
from fastapi.middleware.cors import CORSMiddleware

# Load env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# API Key setup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

client = OpenAI(api_key=api_key)

# Enable CORS for all origins (for development)
app = FastAPI(
    title="Resume AI Service",
    version="1.0.0",
    description="Chat + Resume Grading + PDF Upload"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Pydantic Models
# ---------------------------


class ChatRequest(BaseModel):
    message: str


class MatchRequest(BaseModel):
    job_description: str
    resume_text: str


# ---------------------------
# Helper: Call OpenAI
# ---------------------------
def call_chat_model(messages, model="gpt-4.1-mini"):
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")


# ---------------------------
# Chatbot Logic
# ---------------------------
def get_bot_reply(user_message: str) -> str:
    lower_msg = user_message.lower()

    if any(greeting in lower_msg for greeting in ["hello", "hi", "hey"]):
        return "Hello! How can I assist you today?"

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


@app.post("/chat/")
def chat(request: ChatRequest):
    reply = get_bot_reply(request.message)
    return {"reply": reply}


# ---------------------------
# Resume Grading Logic
# ---------------------------


def grade_resume_against_job(job_description: str, resume_text: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert recruiter and resume reviewer.\n"
                "Given a job description and a resume, evaluate how well they match.\n"
                "Respond ONLY in valid JSON with this exact schema:\n\n"
                "{\n"
                '  "match_score": number,            // 0-100\n'
                '  "summary": string,               // short summary\n'
                '  "strengths": [string, ...],      // 3-5 bullet points\n'
                '  "gaps": [string, ...],           // 3-5 bullet points\n'
                '  "improvements": [string, ...]    // concrete suggestions\n'
                "}\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"JOB DESCRIPTION:\n{job_description}\n\n"
                f"RESUME:\n{resume_text}"
            ),
        },
    ]

    raw = call_chat_model(messages)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # fallback if model returns something slightly off
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON. Try again or adjust the prompt."
        )

    return data


@app.post("/grade_resume/")
def grade_resume(request: MatchRequest):
    evaluation = grade_resume_against_job(
        job_description=request.job_description,
        resume_text=request.resume_text,
    )
    return {"evaluation": evaluation}


# ---------------------------
# PDF Extraction Helper
# ---------------------------
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {e}")

    pages_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)

    final_text = "\n".join(pages_text).strip()

    if not final_text:
        raise HTTPException(
            status_code=400,
            detail="PDF uploaded but no text could be extracted."
        )

    return final_text


# ---------------------------
# PDF Upload Endpoint
# ---------------------------
@app.post("/grade_resume_pdf/")
async def grade_resume_pdf(
    job_description: str = Form(...),
    resume_pdf: UploadFile = File(...),
):
    if resume_pdf.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {resume_pdf.content_type}. Upload a PDF."
        )

    pdf_bytes = await resume_pdf.read()
    resume_text = extract_text_from_pdf_bytes(pdf_bytes)

    evaluation = grade_resume_against_job(job_description, resume_text)

    return {
        "evaluation": evaluation,
        "resume_preview": resume_text[:800],  # helpful for debugging
    }
