import time, uuid
from typing import Any, Dict, Optional, List
from google.cloud import firestore

_firestore_client = None

def get_client():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client()
    return _firestore_client

def now_ms() -> int:
    return int(time.time() * 1000)

def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def session_ref(session_id: str):
    return get_client().collection("sessions").document(session_id)

def trial_ref(session_id: str, trial: int):
    return session_ref(session_id).collection("trials").document(f"trial_{trial}")

def events_col(session_id: str):
    return session_ref(session_id).collection("events")

def log_event(session_id: str, type_: str, text: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    e = {"type": type_, "text": text, "meta": meta or {}, "ts_ms": now_ms()}
    events_col(session_id).document(new_id("e_")).set(e)
    return e

def create_session(protocol_id: str, num_trials: int, user_id: Optional[str]) -> Dict[str, Any]:
    sid = new_id("s_")
    data = {
        "protocol_id": protocol_id,
        "num_trials": num_trials,
        "user_id": user_id,
        "current_trial": 1,
        "created_ts_ms": now_ms(),
        "status": "active",
        "deviations": [],
    }
    session_ref(sid).set(data)
    log_event(sid, "session_started", f"Session started for protocol {protocol_id}", {"num_trials": num_trials})
    for t in range(1, num_trials + 1):
        trial_ref(sid, t).set({"values": {}, "created_ts_ms": now_ms()})
    return {"session_id": sid, **data}

def get_session(session_id: str) -> Dict[str, Any]:
    doc = session_ref(session_id).get()
    if not doc.exists:
        raise KeyError("Session not found")
    return doc.to_dict()

def set_trial_value(session_id: str, trial: int, key: str, value: Any, unit: Optional[str], note: Optional[str]):
    tref = trial_ref(session_id, trial)
    tdoc = tref.get()
    if not tdoc.exists:
        raise KeyError("Trial not found")

    payload = {"value": value, "updated_ts_ms": now_ms()}
    if unit: payload["unit"] = unit
    if note: payload["note"] = note

    tref.set({"values": {key: payload}}, merge=True)
    log_event(session_id, "trial_value_set", f"Trial {trial}: set {key}", {"trial": trial, "key": key, **payload})

def get_trial_values(session_id: str, trial: int) -> Dict[str, Any]:
    doc = trial_ref(session_id, trial).get()
    if not doc.exists:
        raise KeyError("Trial not found")
    return doc.to_dict().get("values", {})

def list_completed_trials(session_id: str, num_trials: int) -> List[int]:
    completed = []
    for t in range(1, num_trials + 1):
        vals = get_trial_values(session_id, t)
        if len(vals) > 0:
            completed.append(t)
    return completed
