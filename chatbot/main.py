from fastapi import FastAPI, HTTPException
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


class MatchRequest(BaseModel):
    job_description: str   # job post text
    resume_text: str       # PDF already converted to plain text


def get_bot_reply(user_message):
    user_message = user_message.lower()
    if "hello" in user_message or "hi" in user_message:
        return "Hello! How can I assist you today?"
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "act as a top level advisor and anser the flooing qution " + user_message}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"


@app.post("/chat/")
def chat(request: ChatRequest):
    reply = get_bot_reply(request.message)
    return ({"reply": reply})


def grade_resume_against_job(job_description: str, resume_text: str) -> str:
    """
    Uses OpenAI to evaluate how well the resume matches the job description.
    Returns a human-readable string with a score + feedback.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert recruiter and resume reviewer. "
                        "Given a job description and a candidate resume, "
                        "evaluate how well the resume matches the job.\n\n"
                        "Your response MUST include:\n"
                        "- A match score from 0 to 100 (label it clearly)\n"
                        "- 3–5 bullet points on key strengths\n"
                        "- 3–5 bullet points on gaps or missing skills\n"
                        "- Concrete suggestions to improve the resume for this specific job"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"JOB DESCRIPTION:\n{job_description}\n\n"
                        f"RESUME:\n{resume_text}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        # In an API it's better to raise an HTTP error instead of returning an error string
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")


@app.post("/grade_resume/")
def grade_resume(request: MatchRequest):
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
    return {"evaluation": evaluation}
