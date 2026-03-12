from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_mastery_tracker
from app.schemas.mastery import MasteryGradeRequest, MasteryGradeResponse
from app.services.mastery_tracker import MasteryTracker, MasteryTrackerError

router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.post("/grade", response_model=MasteryGradeResponse, status_code=status.HTTP_200_OK)
def grade_mastery(
    request: MasteryGradeRequest,
    mastery_tracker: MasteryTracker = Depends(get_mastery_tracker),
) -> MasteryGradeResponse:
    try:
        record = mastery_tracker.update_score(request.student_id, request.skill_id, request.latest_score)
    except MasteryTrackerError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return MasteryGradeResponse.model_validate(record)
