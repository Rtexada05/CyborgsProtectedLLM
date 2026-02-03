"""
Chat endpoint with protection mechanisms
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ...models.schemas import ChatRequest, ChatResponse
from ...controller.defense_controller import DefenseController

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize defense controller
defense_controller = DefenseController()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat request with protection mechanisms"""
    try:
        # Process the request through defense controller
        response = await defense_controller.handle_request(
            user_id=request.user_id,
            prompt=request.prompt,
            mode=request.mode,
            attachments=request.attachments
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )
