"""
Chat endpoint with protection mechanisms
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ...models.schemas import ChatRequest, ChatResponse
from ...controller.defense_controller import DefenseController
from ...services.mode_manager import shared_mode_manager

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize defense controller
defense_controller = DefenseController()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat request with protection mechanisms"""
    try:
        # Always use the global security mode (ignore request mode)
        current_mode = shared_mode_manager.get_mode().value
        
        # Process the request through defense controller
        response = await defense_controller.handle_request(
            user_id=request.user_id,
            prompt=request.prompt,
            mode=current_mode,
            attachments=request.attachments,
            requested_tools=request.requested_tools
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )
