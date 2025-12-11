import random
import logging
from fastapi import FastAPI
from pydantic import BaseModel

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRecruiter")

# Initialize FastAPI
app = FastAPI(title="Smart Candidate Aggregator Live Demo")

# --- MOCK LOGIC (Pure Python - No Heavy Libraries) ---

def mock_parse_jd(text: str):
    # Simulates AI extraction without needing OpenAI API
    skills = ["Java", "Python", "AWS"]
    visa_req = "Citizen/GC" if "Citizen" in text else "None"
    return {"skills": skills, "visa_constraint": visa_req}

def mock_pdl_search(skills):
    # Simulates finding people in a database
    return [
        {
            "name": "Sarah Jones", 
            "status_inference": "Citizen/GC", # Simulated inference
            "email": "sarah.j@example.com",
            "relevant_skills": ["Java", "AWS"] 
        },
        {
            "name": "Alex Chen", 
            "status_inference": "H1B", 
            "email": "alex.c@example.com",
            "relevant_skills": ["Java"] 
        },
        {
            "name": "Rahul V", 
            "status_inference": "Foreign", 
            "email": "rahul.v@example.com",
            "relevant_skills": ["Java"] 
        }
    ]

# --- API MODELS ---
class JobRequest(BaseModel):
    title: str
    description: str
    visa_requirement: str = "Citizen/GC"

class BenchRequest(BaseModel):
    name: str
    resume_text: str

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "System Online", "message": "Go to /docs to use the Dashboard"}

@app.post("/automations/source-candidates")
def source_candidates(job: JobRequest):
    """
    Simulates sourcing workflow: 
    1. Parse JD -> 2. Search DB -> 3. Apply Visa Logic -> 4. Return Verified
    """
    # 1. Parse (Mock)
    parsed = mock_parse_jd(job.description)
    
    # 2. Search (Mock)
    raw_candidates = mock_pdl_search(parsed['skills'])
    
    verified_list = []
    
    # 3. Filter Logic (The 'Secret Sauce')
    for cand in raw_candidates:
        # Check if candidate matches visa requirement
        if job.visa_requirement == "Citizen/GC" and cand['status_inference'] != "Citizen/GC":
            continue # Skip non-citizens
            
        # 4. Add to verified list with a Mock Match Score
        verified_list.append({
            "name": cand['name'],
            "visa_status": cand['status_inference'],
            "match_score": f"{random.randint(88, 99)}%",
            "email": cand['email'],
            "action": "Ready to Interview"
        })
        
    return {
        "job_title": job.title,
        "total_found": len(raw_candidates),
        "verified_candidates": verified_list
    }

@app.post("/automations/market-bench")
def market_bench(consultant: BenchRequest):
    """
    Simulates finding jobs for your bench consultant
    """
    # Mock Jobs
    jobs = [
        {"title": "Senior Developer", "company": "TechGlobal Inc", "match": "95%"},
        {"title": "Backend Lead", "company": "DataSystems", "match": "91%"}
    ]
    
    # Generate Email Pitch
    pitch = f"Hi Hiring Manager,\n\nI have a consultant, {consultant.name}, who is a perfect match for your opening. They are available immediately.\n\nBest,\nRecruiting Team"
    
    return {
        "consultant": consultant.name,
        "matched_jobs": jobs,
        "generated_email_draft": pitch
    }

# Entry point for the server
if __name__ == "__main__":
    import uvicorn
    # Listen on port 10000 for Render
    uvicorn.run(app, host="0.0.0.0", port=10000)
