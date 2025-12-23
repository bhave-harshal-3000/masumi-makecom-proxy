"""
Masumi Make.com Proxy Server
Simple proxy that connects Masumi payment system to Make.com webhooks
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import os
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Masumi Make.com Proxy",
    description="Connects Masumi payments to Make.com webhooks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment variables
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
AGENT_IDENTIFIER = os.getenv("AGENT_IDENTIFIER", "linkedin-outreach-generator")
SELLER_VKEY = os.getenv("SELLER_VKEY")
PAYMENT_AMOUNT = os.getenv("PAYMENT_AMOUNT", "10000000")
PAYMENT_UNIT = os.getenv("PAYMENT_UNIT", "lovelace")
PORT = int(os.getenv("PORT", "8000"))

# In-memory job storage (use Redis/DB in production)
jobs = {}

# Request/Response Models
class InputDataItem(BaseModel):
    key: str
    value: str

class StartJobRequest(BaseModel):
    identifier_from_purchaser: str
    input_data: List[InputDataItem]

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

# MIP-003 Endpoint 1: Input Schema
@app.get("/input_schema")
async def get_input_schema():
    """Returns the expected input schema for the agent"""
    return {
        "csv_url": {
            "type": "string",
            "description": "URL to CSV file containing contact information (Name, Email, Company, Website columns)",
            "required": True,
            "example": "https://example.com/contacts.csv"
        }
    }

# MIP-003 Endpoint 2: Availability Check
@app.get("/availability")
async def check_availability():
    """Health check endpoint"""
    try:
        # Check if Make.com webhook is configured
        if not MAKE_WEBHOOK_URL:
            return {
                "status": "unavailable",
                "message": "Make.com webhook not configured"
            }
        
        # Check if payment service is configured
        if not PAYMENT_SERVICE_URL or not PAYMENT_API_KEY:
            return {
                "status": "unavailable",
                "message": "Payment service not configured"
            }
        
        return {
            "status": "available",
            "message": "LinkedIn Outreach Email Generator is online",
            "uptime": "operational"
        }
    except Exception as e:
        logger.error(f"Availability check failed: {e}")
        return {
            "status": "unavailable",
            "message": str(e)
        }

# MIP-003 Endpoint 3: Start Job (with Payment)
@app.post("/start_job")
async def start_job(request: StartJobRequest):
    """
    Start a new job with payment integration
    1. Creates payment request
    2. Returns payment details to user
    3. Monitors payment in background
    4. Executes Make.com webhook when paid
    """
    try:
        # Validate configuration
        if not MAKE_WEBHOOK_URL:
            raise HTTPException(status_code=500, detail="Make.com webhook not configured")
        
        if not PAYMENT_SERVICE_URL or not PAYMENT_API_KEY:
            raise HTTPException(status_code=500, detail="Payment service not configured")
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        logger.info(f"[Job {job_id}] Creating payment request...")
        
        # Create payment request via Masumi Payment Service
        async with httpx.AsyncClient(timeout=30.0) as client:
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/payment/",
                json={
                    "agentIdentifier": AGENT_IDENTIFIER,
                    "sellerVKey": SELLER_VKEY,
                    "identifierFromPurchaser": request.identifier_from_purchaser,
                    "amounts": [{
                        "amount": PAYMENT_AMOUNT,
                        "unit": PAYMENT_UNIT
                    }],
                    "inputData": [item.dict() for item in request.input_data]
                },
                headers={
                    "x-api-key": PAYMENT_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            if payment_response.status_code != 200:
                raise HTTPException(
                    status_code=payment_response.status_code,
                    detail=f"Payment service error: {payment_response.text}"
                )
            
            payment_data = payment_response.json()
        
        # Store job with pending status
        jobs[job_id] = {
            "status": "awaiting_payment",
            "input_data": [item.dict() for item in request.input_data],
            "payment": payment_data,
            "identifier_from_purchaser": request.identifier_from_purchaser,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Start background task to monitor payment
        asyncio.create_task(monitor_payment_and_execute(job_id, payment_data.get("blockchainIdentifier")))
        
        logger.info(f"[Job {job_id}] Payment request created successfully")
        
        # Return payment details to user
        return {
            "status": "success",
            "job_id": job_id,
            "message": "Payment request created. Please send payment to proceed.",
            **payment_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MIP-003 Endpoint 4: Job Status
@app.get("/status")
async def get_job_status(job_id: str):
    """Check the status of a job"""
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        message=job.get("message", "Job in progress"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at")
    )

# Background task: Monitor payment and execute Make.com
async def monitor_payment_and_execute(job_id: str, blockchain_identifier: str):
    """
    Background task that:
    1. Polls payment status
    2. When paid, calls Make.com webhook
    3. Stores result
    """
    max_attempts = 60  # 5 minutes with 5-second intervals
    attempt = 0
    
    logger.info(f"[Job {job_id}] Starting payment monitoring...")
    
    while attempt < max_attempts:
        attempt += 1
        await asyncio.sleep(5)  # Check every 5 seconds
        
        try:
            # Check payment status
            async with httpx.AsyncClient(timeout=10.0) as client:
                payment_status_response = await client.post(
                    f"{PAYMENT_SERVICE_URL}/payment/resolve-blockchain-identifier",
                    json={"blockchainIdentifier": blockchain_identifier},
                    headers={
                        "x-api-key": PAYMENT_API_KEY,
                        "Content-Type": "application/json"
                    }
                )
                
                if payment_status_response.status_code != 200:
                    logger.error(f"[Job {job_id}] Payment status check failed: {payment_status_response.text}")
                    continue
                
                payment_status = payment_status_response.json()
            
            # Check if payment is confirmed
            if payment_status.get("status") == "paid":
                logger.info(f"[Job {job_id}] Payment confirmed! Executing Make.com webhook...")
                
                # Update job status
                jobs[job_id]["status"] = "running"
                
                # Execute Make.com webhook
                result = await execute_makecom_webhook(job_id)
                
                # Store result
                jobs[job_id]["status"] = result["status"]
                jobs[job_id]["result"] = result.get("output")
                jobs[job_id]["message"] = result.get("message", "Job completed")
                jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                
                logger.info(f"[Job {job_id}] Completed with status: {result['status']}")
                return
                
        except Exception as e:
            logger.error(f"[Job {job_id}] Payment monitoring error: {e}")
            continue
    
    # Timeout - payment not received
    logger.warning(f"[Job {job_id}] Payment timeout - no payment received within 5 minutes")
    jobs[job_id]["status"] = "payment_timeout"
    jobs[job_id]["message"] = "Payment not received within 5 minutes"
    jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

# Execute Make.com webhook
async def execute_makecom_webhook(job_id: str) -> Dict[str, Any]:
    """
    Calls Make.com webhook with job data
    Returns the result from Make.com
    """
    try:
        job = jobs[job_id]
        
        # Convert input_data to simple dict for Make.com
        make_payload = {}
        for item in job["input_data"]:
            make_payload[item["key"]] = item["value"]
        
        # Add job_id for tracking
        make_payload["job_id"] = job_id
        make_payload["identifier_from_purchaser"] = job.get("identifier_from_purchaser")
        
        logger.info(f"[Job {job_id}] Calling Make.com webhook...")
        logger.debug(f"[Job {job_id}] Payload: {make_payload}")
        
        # Call Make.com with extended timeout (5 minutes)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                MAKE_WEBHOOK_URL,
                json=make_payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"[Job {job_id}] Make.com webhook completed successfully")
            
            return {
                "status": "completed",
                "output": result,
                "message": "Make.com processing completed"
            }
            
    except httpx.TimeoutException:
        logger.error(f"[Job {job_id}] Make.com webhook timeout (>5 minutes)")
        return {
            "status": "error",
            "message": "Make.com webhook timeout - processing took longer than 5 minutes"
        }
    except httpx.HTTPError as e:
        logger.error(f"[Job {job_id}] Make.com webhook HTTP error: {e}")
        return {
            "status": "error",
            "message": f"Make.com webhook error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"[Job {job_id}] Make.com webhook unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Masumi Make.com Proxy",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "input_schema": "/input_schema",
            "availability": "/availability",
            "start_job": "/start_job (POST)",
            "job_status": "/status?job_id=xxx"
        }
    }

# Health check
@app.get("/health")
async def health():
    """Simple health check"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
