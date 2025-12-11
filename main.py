import os
import json
import logging
import random
from typing import List, Optional
from datetime import datetime
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRecruiter")
app = FastAPI(title="Smart Candidate Aggregator Live Demo")

# --- MOCK DB & LOGIC ---
# We use mocks here so you can see it working immediately on the Free Tier

def mock_get_embedding(text: str):
    # Simulates an AI Vector (List of 1536 floats)
    return np.random.rand(1536).tolist()

def mock_parse_jd(text: str):
    # Simulates GPT-4 extracting skills
    return {
        "skills": ["Java", "AWS", "Spring Boot"], 
        "visa_constraint": "Citizen/GC" if "Citizen" in text else "None"
    }

def mock_pdl_search(skills):
    # Simulates People Data Labs returning real profiles
    return [
        {"name": "Sarah Jones", "skills": ["Java", "AWS"], "edu": [{"country": "US", "year": "2012"}], "email": "sarah.j@example.com"},
        {"name": "Alex Chen", "skills": ["Java", "Spring"], "edu": [{"country": "China", "year": "2018"}, {"country": "US", "year": "2020"}], "email": "alex.c@example.com"},
        {"name": "Rahul V", "skills": ["Java"], "edu": [{"country": "India", "year": "2022"}], "email": "rahul.v@example.com"}
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
    return {"status": "System Online", "message": "Go to /docs to test the AI"}

@app.post("/automations/source-candidates")
def source_candidates(job: JobRequest):
    """
    Simulates the full sourcing workflow:
    1. Parse JD -> 2. Search PDL -> 3. Infer Visa -> 4. Rank
    """
    # 1. Parse
    parsed = mock_parse_jd(job.description)
    
    # 2. Search
    candidates = mock_pdl_search(parsed['skills'])
    verified = []

    # 3. Filter (The "Secret Sauce")
    for cand in candidates:
        # Visa Logic: If US Degree > 8 years ago = Citizen
        edu = cand['edu'][-1]
        is_citizen = True if edu['country'] == "US" and int(edu['year']) < 2016 else False
        
        status = "Citizen/GC" if is_citizen else "H1B/OPT"
        
        # Hard Filter
        if job.visa_requirement == "Citizen/GC" and status != "Citizen/GC":
            continue 

        # 4. Rank
        verified.append({
            "name": cand['name'],
            "status": "VERIFIED",
            "visa": status,
            "match_score": f"{random.randint(89, 99)}%",
            "email": cand['email']
        })
    
    return {"verified_candidates": verified, "hidden_candidates": len(candidates) - len(verified)}

@app.post("/automations/market-bench")
def market_bench(consultant: BenchRequest):
    """
    Simulates finding jobs for your bench consultant.
    """
    # Mock Jobs found in market
    jobs = [
        {"title": "Sr Java Lead", "company": "TechFlow", "match": "95%"},
        {"title": "Java Backend Dev", "company": "DataCorp", "match": "88%"}
    ]
    
    # Generate Email Pitch
    pitch = f"Hi Hiring Manager, I have a consultant {consultant.name} perfect for your role. They have 10+ years exp. Attached is the resume."
    
    return {"matched_jobs": jobs, "auto_generated_email": pitch}
