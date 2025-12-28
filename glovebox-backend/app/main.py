from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict
import os 
import requests
from fastapi import HTTPException

from .models import (
    SessionStartRequest, SessionStartResponse,
    TrialSetValueRequest, TrialGetValuesResponse,
    TrialCompareRequest, TrialCompareResponse,
    SessionSummaryRequest, SessionSummaryResponse,
    EventLogRequest
)
from .db import (
    create_session, get_session, set_trial_value, get_trial_values,
    log_event, list_completed_trials
)
from .llm import compare_trials_nl
from .protocols import PROTOCOLS

app = FastAPI(title="GloveBox Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/session/start", response_model=SessionStartResponse)
def session_start(req: SessionStartRequest):
    if req.protocol_id not in PROTOCOLS:
        raise HTTPException(status_code=400, detail="Unknown protocol_id")
    s = create_session(req.protocol_id, req.num_trials, req.user_id)
    return SessionStartResponse(
        session_id=s["session_id"],
        protocol_id=s["protocol_id"],
        num_trials=s["num_trials"],
        current_trial=s["current_trial"]
    )

@app.post("/trial/set_value")
def trial_set_value(req: TrialSetValueRequest):
    try:
        s = get_session(req.session_id)
        if req.trial > s["num_trials"]:
            raise HTTPException(status_code=400, detail="trial exceeds num_trials")
        set_trial_value(req.session_id, req.trial, req.key, req.value, req.unit, req.note)
        return {"ok": True, "session_id": req.session_id, "trial": req.trial, "key": req.key}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/trial/get_values", response_model=TrialGetValuesResponse)
def trial_get_values(session_id: str, trial: int):
    try:
        values = get_trial_values(session_id, trial)
        return TrialGetValuesResponse(session_id=session_id, trial=trial, values=values)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/trial/compare", response_model=TrialCompareResponse)
def trial_compare(req: TrialCompareRequest):
    try:
        a = get_trial_values(req.session_id, req.trial_a)
        b = get_trial_values(req.session_id, req.trial_b)

        keys = set(a.keys()) | set(b.keys())
        diff: Dict[str, Dict[str, Any]] = {}
        for k in keys:
            va = a.get(k)
            vb = b.get(k)
            if va != vb:
                diff[k] = {"trial_a": va, "trial_b": vb}

        nl = compare_trials_nl(a, b)
        log_event(req.session_id, "trial_compared", f"Compared trial {req.trial_a} vs {req.trial_b}",
                  {"trial_a": req.trial_a, "trial_b": req.trial_b, "diff_keys": list(diff.keys())})

        return TrialCompareResponse(
            session_id=req.session_id,
            trial_a=req.trial_a,
            trial_b=req.trial_b,
            diff=diff,
            natural_language=nl
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/session/summary", response_model=SessionSummaryResponse)
def session_summary(req: SessionSummaryRequest):
    try:
        s = get_session(req.session_id)
        completed = list_completed_trials(req.session_id, s["num_trials"])
        deviations = s.get("deviations", [])
        protocol = PROTOCOLS.get(s["protocol_id"], {})
        next_suggestion = "Continue with the next trial and store your key measurements."
        spoken = (
            f"You’re running {protocol.get('name','a protocol')}. "
            f"You’ve stored values for {len(completed)} out of {s['num_trials']} trials. "
            f"There are {len(deviations)} deviations logged. "
            f"Next: continue with Trial {min(len(completed)+1, s['num_trials'])}."
        )
        log_event(req.session_id, "session_summary_requested", "Session summary requested", {})
        return SessionSummaryResponse(
            session_id=req.session_id,
            protocol_id=s["protocol_id"],
            num_trials=s["num_trials"],
            completed_trials=completed,
            deviations=deviations,
            next_suggestion=next_suggestion,
            spoken_summary=spoken
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/event/log")
def event_log(req: EventLogRequest):
    try:
        _ = get_session(req.session_id)
        e = log_event(req.session_id, req.type, req.text, req.meta)
        return {"ok": True, "event": e}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@app.get("/elevenlabs/token")
def elevenlabs_token():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    if not api_key or not agent_id:
        raise HTTPException(status_code=500, detail="Missing ELEVENLABS_API_KEY or ELEVENLABS_AGENT_ID")

    r = requests.get(
        "https://api.elevenlabs.io/v1/convai/conversation/token",
        headers={"xi-api-key": api_key},
        params={"agent_id": agent_id},
        timeout=20,
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"Token error {r.status_code}: {r.text}")

    # This returns JSON (typically includes a conversation_token)
    return r.json()
