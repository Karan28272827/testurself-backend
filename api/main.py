import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    print("Warning: DEEPSEEK_API_KEY not set. Set it in .env")

app = FastAPI(title="DeepSeek Learning Bot")
frontend_url = "https://testurself-frontend.vercel.app/"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Store your document content here
DOCUMENT_CONTENT = """
[Replace this with your actual document content]
For example:
The Python programming language was created by Guido van Rossum and first released in 1991.
Python emphasizes code readability with significant whitespace.
It supports multiple programming paradigms including procedural, object-oriented, and functional programming.
"""

class EvaluateRequest(BaseModel):
    question: str
    user_answer: str

async def call_deepseek(prompt: str, temperature: float = 0.7) -> str:
    """Helper function to call DeepSeek API"""
    deepseek_url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    json_payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 800
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(deepseek_url, json=json_payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=500, 
                detail=f"DeepSeek error: {resp.status_code} {resp.text}"
            )
        data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid response from DeepSeek")

@app.post("/generate-question")
async def generate_question():
    """
    Generate a question based on the document content
    """
    prompt = f"""Based on the following document, generate ONE specific question that tests understanding of the content.
The question should be clear, specific, and answerable from the document.
Only return the question itself, nothing else.

Document:
{DOCUMENT_CONTENT}

Question:"""

    question = await call_deepseek(prompt, temperature=0.8)
    return {"question": question.strip()}

@app.post("/evaluate-answer")
async def evaluate_answer(payload: EvaluateRequest):
    """
    Evaluate if the user's answer is correct and provide justification
    """
    prompt = f"""You are evaluating a student's answer to a question based on a document.

Document:
{DOCUMENT_CONTENT}

Question: {payload.question}

Student's Answer: {payload.user_answer}

Evaluate if the student's answer is correct based on the document content.
Respond in this exact format:

VERDICT: [CORRECT or INCORRECT]
JUSTIFICATION: [Explain why the answer is correct or incorrect. If incorrect, provide the correct answer and explain what was wrong with the student's response. If correct, explain what made it a good answer.]
"""

    response = await call_deepseek(prompt, temperature=0.3)
    
    # Parse the response
    lines = response.strip().split('\n')
    verdict_line = ""
    justification = ""
    
    for line in lines:
        if line.startswith("VERDICT:"):
            verdict_line = line.replace("VERDICT:", "").strip().upper()
        elif line.startswith("JUSTIFICATION:"):
            justification = line.replace("JUSTIFICATION:", "").strip()
        elif justification:  # Continue multi-line justification
            justification += " " + line.strip()
    
    is_correct = "CORRECT" in verdict_line and "INCORRECT" not in verdict_line
    
    return {
        "is_correct": is_correct,
        "justification": justification or response
    }

@app.get("/")
async def root():
    return {"message": "DeepSeek Learning Bot API"}