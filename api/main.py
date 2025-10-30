# import os
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from dotenv import load_dotenv
# import httpx
# from fastapi.middleware.cors import CORSMiddleware

# load_dotenv()

# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# if not DEEPSEEK_API_KEY:
#     print("Warning: DEEPSEEK_API_KEY not set. Set it in .env")

# app = FastAPI(title="DeepSeek Learning Bot")
# frontend_url = "https://testurself-frontend.vercel.app/"

# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=r"https://testurself-frontend.*\.vercel\.app",
#     allow_origins=[
#         frontend_url,
#         "http://localhost:3000",
#         "http://127.0.0.1:3000"
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # Store your document content here
# DOCUMENT_CONTENT = """
# [Replace this with your actual document content]
# For example:
# The Python programming language was created by Guido van Rossum and first released in 1991.
# Python emphasizes code readability with significant whitespace.
# It supports multiple programming paradigms including procedural, object-oriented, and functional programming.
# """

# class EvaluateRequest(BaseModel):
#     question: str
#     user_answer: str

# async def call_deepseek(prompt: str, temperature: float = 0.7) -> str:
#     """Helper function to call DeepSeek API"""
#     deepseek_url = "https://api.deepseek.com/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     json_payload = {
#         "model": "deepseek-chat",
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": temperature,
#         "max_tokens": 800
#     }

#     async with httpx.AsyncClient(timeout=30.0) as client:
#         resp = await client.post(deepseek_url, json=json_payload, headers=headers)
#         if resp.status_code >= 400:
#             raise HTTPException(
#                 status_code=500, 
#                 detail=f"DeepSeek error: {resp.status_code} {resp.text}"
#             )
#         data = resp.json()

#     try:
#         return data["choices"][0]["message"]["content"]
#     except Exception:
#         raise HTTPException(status_code=500, detail="Invalid response from DeepSeek")

# @app.post("/generate-question")
# async def generate_question():
#     """
#     Generate a question based on the document content
#     """
#     prompt = f"""Based on the following document, generate ONE specific question that tests understanding of the content.
# The question should be clear, specific, and answerable from the document.
# Only return the question itself, nothing else.

# Document:
# {DOCUMENT_CONTENT}

# Question:"""

#     question = await call_deepseek(prompt, temperature=0.8)
#     return {"question": question.strip()}

# @app.post("/evaluate-answer")
# async def evaluate_answer(payload: EvaluateRequest):
#     """
#     Evaluate if the user's answer is correct and provide justification
#     """
#     prompt = f"""You are evaluating a student's answer to a question based on a document.

# Document:
# {DOCUMENT_CONTENT}

# Question: {payload.question}

# Student's Answer: {payload.user_answer}

# Evaluate if the student's answer is correct based on the document content.
# Respond in this exact format:

# VERDICT: [CORRECT or INCORRECT]
# JUSTIFICATION: [Explain why the answer is correct or incorrect. If incorrect, provide the correct answer and explain what was wrong with the student's response. If correct, explain what made it a good answer.]
# """

#     response = await call_deepseek(prompt, temperature=0.3)
    
#     # Parse the response
#     lines = response.strip().split('\n')
#     verdict_line = ""
#     justification = ""
    
#     for line in lines:
#         if line.startswith("VERDICT:"):
#             verdict_line = line.replace("VERDICT:", "").strip().upper()
#         elif line.startswith("JUSTIFICATION:"):
#             justification = line.replace("JUSTIFICATION:", "").strip()
#         elif justification:  # Continue multi-line justification
#             justification += " " + line.strip()
    
#     is_correct = "CORRECT" in verdict_line and "INCORRECT" not in verdict_line
    
#     return {
#         "is_correct": is_correct,
#         "justification": justification or response
#     }

# @app.get("/")
# async def root():
#     return {"message": "DeepSeek Learning Bot API"}


import time
import os
from fastapi import FastAPI, HTTPException, Query
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
    allow_origin_regex=r"https://testurself-frontend.*\.vercel\.app",
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    question: str
    user_answer: str

# In-memory cache with timestamp for questions
doc_cache = {
    "content": None,
    "questions": None,
    "doc_url": None,
    "last_update": 0,
}

async def call_deepseek(prompt: str, temperature: float = 0.7) -> str:
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
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(deepseek_url, json=json_payload, headers=headers)
        print(resp.text)
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

@app.get("/generate-from-doc")
async def generate_from_doc(doc_url: str = Query(..., description="Google Doc published-to-web URL (e.g. .../pub or .../pub?output=txt)")):
    now = time.time()

    cache_valid = (doc_cache["doc_url"] == doc_url and
                   doc_cache["content"] is not None and
                   doc_cache["questions"] is not None and
                   now - doc_cache["last_update"] < 120)

    if cache_valid:
        print("Using cached document and questions")
        return {"generated_questions": doc_cache["questions"]}

    async with httpx.AsyncClient() as client:
        resp = await client.get(doc_url)
        print(f"Doc fetch status: {resp.status_code}")
        print(f"First 500 chars fetched:\n{resp.text[:500]}")
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Unable to fetch doc content.")
        doc_text = resp.text

    prompt = f"""
Read the following document and generate exactly 5 objective questions with answers followed by 5 subjective questions with answers.

Format exactly:

Objective Questions:
1. Question ...
Answer: ...
2. Question ...
Answer: ...
3. Question ...
Answer: ...
4. Question ...
Answer: ...
5. Question ...
Answer: ...

Subjective Questions:
1. Question ...
Answer: ...
2. Question ...
Answer: ...
3. Question ...
Answer: ...
4. Question ...
Answer: ...
5. Question ...
Answer: ...

Document:
{doc_text}
"""

    questions = await call_deepseek(prompt, temperature=0.8)

    doc_cache["doc_url"] = doc_url
    doc_cache["content"] = doc_text
    doc_cache["questions"] = questions.strip()
    doc_cache["last_update"] = now

    return {"generated_questions": questions.strip()}

@app.post("/generate-question")
async def generate_question():
    default_doc = """
    The Python programming language was created by Guido van Rossum and first released in 1991.
    """
    prompt = f"""Based on the following document, generate ONE specific question that tests understanding of the content.
The question should be clear, specific, and answerable from the document.
Only return the question itself, nothing else.

Document:
{default_doc}

Question:"""
    question = await call_deepseek(prompt, temperature=0.8)
    return {"question": question.strip()}

@app.post("/evaluate-answer")
async def evaluate_answer(payload: EvaluateRequest):
    prompt = f"""You are evaluating a student's answer to a question based on a document.

Document:
{payload.question}

Student's Answer: {payload.user_answer}

Evaluate if the student's answer is correct based on the document content.

- Ignore punctuation and capitalization differences.
- Accept synonyms and minor paraphrasing if the meaning is still correct, and do not be overly strict on exact wording.
- Be flexible on word order and minor grammatical differences as long as the core information is accurate.
- Do not penalize for minor typos or small irrelevant mistakes.

Respond in this exact format:


VERDICT: [CORRECT or INCORRECT]
JUSTIFICATION: [Explain why the answer is correct or incorrect. If incorrect, provide the correct answer and explain what was wrong with the student's response. If correct, explain what made it a good answer.]
"""
    response = await call_deepseek(prompt, temperature=0.3)
    lines = response.strip().split('\n')
    verdict_line = ""
    justification = ""
    for line in lines:
        if line.startswith("VERDICT:"):
            verdict_line = line.replace("VERDICT:", "").strip().upper()
        elif line.startswith("JUSTIFICATION:"):
            justification = line.replace("JUSTIFICATION:", "").strip()
        elif justification:
            justification += " " + line.strip()
    is_correct = "CORRECT" in verdict_line and "INCORRECT" not in verdict_line
    return {"is_correct": is_correct, "justification": justification or response}

@app.get("/")
async def root():
    return {"message": "DeepSeek Learning Bot API"}
