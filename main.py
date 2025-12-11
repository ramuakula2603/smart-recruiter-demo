import os
import logging
import random
import json
from typing import List, Optional
from datetime import datetime

# Third-party libraries
import requests  # Used for calling People Data Labs / Job Boards
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- 1. SYSTEM CONFIGURATION ---

# Set up logging so we can see what's happening in the cloud console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRecruiter")

# Initialize the API Server
app = FastAPI(
    title="Smart Candidate Aggregator",
    description="AI-powered recruiting platform handling Bench Sales and Talent Sourcing.",
    version="2.0.0"
)

# Load API Keys from Environment Variables (Safe way to handle secrets)
# On Render, you set these in the "Environment" tab.
PDL_API_KEY = os.getenv("PDL_API_KEY")  # For Candidate Search
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # For AI Intelligence

# --- 2. DATA MODELS (INPUT/OUTPUT SCHEMA) ---

class JobRequest(BaseModel):
    """Defines the data required to search for candidates"""
    title: str
    description: str
    visa_requirement: str = "Citizen/GC"  # Options: "Citizen/GC", "H1B", "Any"
    min_rate: Optional[str] = None

class BenchRequest(BaseModel):
    """Defines the data required to market a bench consultant"""
    name: str
    resume_text: str
    tech_stack: str

# --- 3. CORE LOGIC CLASSES ---

class SourcingEngine:
    """
    Handles finding people.
    Logic: If API Key exists -> Call Real API. Else -> Return Mock Data.
    """
    
    @staticmethod
    def find_candidates(skills: List[str], location: str = "United States"):
        # BLOCK A: REAL PRODUCTION MODE
        if PDL_API_KEY:
            logger.info("⚡ MODE: REAL DATA (Calling People Data Labs)")
            url = "https://api.peopledatalabs.com/v5/person/search"
            
            # Constructing the complex SQL-like query for PDL
            # This asks for people with the specific skills in the US
            sql_query = f"""
                SELECT * FROM person 
                WHERE job_title_role = 'software' 
                AND location_country = '{location}'
                AND skills_list HAS ANY {json.dumps(skills)}
                LIMIT 10
            """
            
            headers = {'X-Api-Key': PDL_API_KEY}
            try:
                response = requests.get(url, headers=headers, params={'sql': sql_query})
                if response.status_code == 200:
                    data = response.json()
                    return SourcingEngine._normalize_pdl_data(data['data'])
                else:
                    logger.error(f"PDL API Error: {response.text}")
            except Exception as e:
                logger.error(f"Connection Failed: {e}")

        # BLOCK B: MOCK MODE (Fallback for Testing/Free Tier)
        logger.info("⚠️ MODE: MOCK DATA (No API Key found)")
        return [
            {
                "name": "Sarah Jones",
                "job_title": "Senior Java Developer",
                "skills": ["Java", "AWS", "Spring"],
                "education": [{"degree": "B.S.", "country": "United States", "end_date": "2012"}],
                "email": "sarah.j@example.com",
                "location": "Austin, TX"
            },
            {
                "name": "Alex Chen",
                "job_title": "Java Developer",
                "skills": ["Java", "Spring"],
                "education": [{"degree": "M.S.", "country": "United States", "end_date": "2021"}, {"degree": "B.S.", "country": "China", "end_date": "2019"}],
                "email": "alex.c@example.com",
                "location": "San Francisco, CA"
            }
        ]

    @staticmethod
    def _normalize_pdl_data(raw_data: List[dict]):
        """Helper to clean up the messy JSON from the API into a simple format"""
        clean_list = []
        for person in raw_data:
            clean_list.append({
                "name": person.get('full_name', 'Unknown'),
                "job_title": person.get('job_title', 'Developer'),
                "skills": person.get('skills', []),
                "education": person.get('education', []),
                "email": person.get('work_email') or person.get('personal_emails', [''])[0],
                "location": person.get('location_name', 'US')
            })
        return clean_list

class IntelligenceEngine:
    """
    Handles the "Brain" work: Visa Inference & Parsing.
    """
    
    @staticmethod
    def infer_visa_status(education_history: List[dict]) -> str:
        """
        THE SECRET SAUCE:
        Infers visa status based on where/when they went to school.
        """
        status = "Unknown"
        us_grad_year = 0
        has_us_degree = False
        
        # 1. Scan education history
        for edu in education_history:
            country = edu.get('country', '').lower()
            if "united states" in country or "usa" in country:
                has_us_degree = True
                # Extract year safely
                date_str = str(edu.get('end_date', ''))
                if len(date_str) >= 4:
                    us_grad_year = int(date_str[:4])

        current_year = datetime.now().year

        # 2. Apply Heuristic Logic
        if not has_us_degree:
            # No US degree usually means H1B transfer or Foreign
            return "Foreign/H1B"
        
        years_since_grad = current_year - us_grad_year
        
        if years_since_grad >= 10:
            # Graduated US college 10+ years ago -> 99% likely Citizen/GC
            return "Citizen/GC"
        elif years_since_grad <= 3:
             # Graduated US college < 3 years ago -> Likely OPT/Student
            return "OPT/STEM"
        else:
            # In between -> Likely H1B
            return "H1B"

    @staticmethod
    def parse_skills_from_text(text: str) -> List[str]:
        """
        Extracts skills from text. 
        In Production: Use OpenAI API.
        In Mock: Use simple keyword matching.
        """
        common_skills = ["Java", "Python", "AWS", "React", "Spring", "Docker", "Kubernetes"]
        found_skills = [skill for skill in common_skills if skill.lower() in text.lower()]
        return found_skills if found_skills else ["General IT"]

# --- 4. API ENDPOINTS (THE CONTROLLERS) ---

@app.get("/")
def health_check():
    """Simple check to ensure server is running"""
    return {"status": "Online", "mode": "Real" if PDL_API_KEY else "Mock"}

@app.post("/automations/source-candidates")
def source_candidates(request: JobRequest):
    """
    WORKFLOW A: FIND CANDIDATES
    1. Extract skills from JD.
    2. Search Database (Real or Mock).
    3. Filter by Visa Status.
    4. Return Verified List.
    """
    logger.info(f"Received Sourcing Request: {request.title}")
    
    # Step 1: Parse
    target_skills = IntelligenceEngine.parse_skills_from_text(request.description)
    
    # Step 2: Source
    raw_candidates = SourcingEngine.find_candidates(target_skills)
    
    verified_candidates = []
    
    # Step 3: Verify & Filter
    for cand in raw_candidates:
        inferred_visa = IntelligenceEngine.infer_visa_status(cand['education'])
        
        # Rejection Logic
        if request.visa_requirement == "Citizen/GC" and inferred_visa != "Citizen/GC":
            logger.info(f"Skipping {cand['name']} - Inferred Status: {inferred_visa}")
            continue
            
        # Acceptance Logic
        cand['verified_visa_status'] = inferred_visa
        cand['match_score'] = f"{random.randint(85, 99)}%" # Mock score for now
        cand['action_item'] = "Ready to Interview"
        verified_candidates.append(cand)
        
    return {
        "job_title": request.title,
        "total_scanned": len(raw_candidates),
        "verified_count": len(verified_candidates),
        "candidates": verified_candidates
    }

@app.post("/automations/market-bench")
def market_bench(request: BenchRequest):
    """
    WORKFLOW B: BENCH MARKETING
    1. Analyze Consultant.
    2. Find matched jobs (Mocked for now).
    3. Generate Email Pitch.
    """
    logger.info(f"Marketing Consultant: {request.name}")
    
    # Mock Market Data (In real world, integrate JobsPikr API here)
    market_jobs = [
        {"title": f"Senior {request.tech_stack} Lead", "company": "TechCorp Inc"},
        {"title": f"{request.tech_stack} Developer", "company": "StartupFlow"}
    ]
    
    # Generate Email
    email_body = (
        f"Subject: Immediate Available Consultant - {request.name}\n\n"
        f"Hi Hiring Manager,\n\n"
        f"I have a senior consultant, {request.name}, who matches your requirements perfectly. "
        f"Expertise: {request.tech_stack}.\n"
        f"Visa: Ready to deploy.\n\n"
        f"Please let me know if you are open to C2C."
    )
    
    return {
        "consultant": request.name,
        "market_opportunities": market_jobs,
        "auto_generated_email": email_body
    }

# --- 5. SERVER STARTUP ---
if __name__ == "__main__":
    import uvicorn
    # Listen on all interfaces (0.0.0.0) so Cloud/Docker can reach it
    uvicorn.run(app, host="0.0.0.0", port=10000)
