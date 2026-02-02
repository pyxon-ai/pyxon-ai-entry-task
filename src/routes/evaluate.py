from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from services.evaluation_service import evaluation_service
import logging

logger = logging.getLogger('uvicorn.error')

evaluate_router = APIRouter(
    prefix="/api/v1/evaluate",
    tags=["api_v1", "evaluate"],
)


@evaluate_router.post("/run")
async def run_evaluation(
    app_settings: Settings = Depends(get_settings)
):
    try:
        logger.info("Starting evaluation of all test questions...")
        results = await evaluation_service.run_evaluation()
        
        return {
            "status": "completed",
            "message": "Evaluation completed successfully",
            "summary": results["statistics"],
            "total_questions": results["total_questions"],
            "timestamp": results["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@evaluate_router.get("/results")
async def get_results(
    app_settings: Settings = Depends(get_settings)
):
    try:
        results = evaluation_service.get_latest_results()
        
        if "error" in results:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=results
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Error fetching results: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@evaluate_router.get("/statistics")
async def get_statistics(
    app_settings: Settings = Depends(get_settings)
):
    try:
        results = evaluation_service.get_latest_results()
        
        if "error" in results:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=results
            )
        
        return results.get("statistics", {})
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )
