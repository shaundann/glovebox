from typing import Dict, Any

def compare_trials_nl(trial_a: Dict[str, Any], trial_b: Dict[str, Any]) -> str:
    keys = sorted(set(trial_a.keys()) | set(trial_b.keys()))
    lines = []
    for k in keys:
        va = trial_a.get(k)
        vb = trial_b.get(k)
        if va == vb:
            continue
        lines.append(
            f"{k}: Trial A={va.get('value') if va else None} {va.get('unit','') if va else ''} | "
            f"Trial B={vb.get('value') if vb else None} {vb.get('unit','') if vb else ''}"
        )
    if not lines:
        return "Trials look identical for the stored values."
    return "Key differences:\n" + "\n".join(lines)
