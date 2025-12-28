from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List

class SessionStartRequest(BaseModel):
    protocol_id: str = "dilution_v1"
    num_trials: int = 3
    user_id: Optional[str] = None

class SessionStartResponse(BaseModel):
    session_id: str
    protocol_id: str
    num_trials: int
    current_trial: int

class TrialSetValueRequest(BaseModel):
    session_id: str
    trial: int = Field(ge=1)
    key: str
    value: Any
    unit: Optional[str] = None
    note: Optional[str] = None

class TrialGetValuesResponse(BaseModel):
    session_id: str
    trial: int
    values: Dict[str, Any]

class TrialCompareRequest(BaseModel):
    session_id: str
    trial_a: int = Field(ge=1)
    trial_b: int = Field(ge=1)

class TrialCompareResponse(BaseModel):
    session_id: str
    trial_a: int
    trial_b: int
    diff: Dict[str, Dict[str, Any]]
    natural_language: Optional[str] = None

class SessionSummaryRequest(BaseModel):
    session_id: str

class SessionSummaryResponse(BaseModel):
    session_id: str
    protocol_id: str
    num_trials: int
    completed_trials: List[int]
    deviations: List[Dict[str, Any]]
    next_suggestion: str
    spoken_summary: str

class EventLogRequest(BaseModel):
    session_id: str
    type: str
    text: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
