# services/ai_planner.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# OpenAI is optional; import lazily
_OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # SDK v2.x
    _OPENAI_AVAILABLE = True
except Exception:
    pass


@dataclass
class PlanContext:
    id: int
    name: str
    goal_type: str
    start_date: Optional[str]
    race_date: Optional[str]
    duration_weeks: int
    max_days_per_week: int
    long_run_day: str
    weekly_increase_cap: float
    long_run_cap: float
    guardrails_enabled: bool


@dataclass
class WorkoutSuggestion:
    date: str
    workout_type: str
    planned_distance: Optional[float] = None
    planned_intensity: Optional[str] = None
    description: Optional[str] = None


class AIPlanner:
    """
    Facade used by the Calendar. If OpenAI is enabled + key present, calls the API,
    otherwise falls back to a deterministic heuristic so the app always works.
    """

    _MODEL_PRICING = {
        # Rough placeholders (USD per 1M tokens). Adjust to your contract if needed.
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4.1-mini": {"input": 0.30, "output": 1.20},
    }

    @staticmethod
    def _estimate_cost(model: str, prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> Optional[float]:
        try:
            p = AIPlanner._MODEL_PRICING.get((model or "").lower())
            if not p or prompt_tokens is None or completion_tokens is None:
                return None
            return (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000.0
        except Exception:
            return None

    def __init__(self, use_openai: bool = False, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self._use_openai = bool(use_openai)
        self._api_key = api_key or ""
        self._model = model

    def set_config(self, use_openai: bool, api_key: Optional[str], model: Optional[str] = None):
        self._use_openai = bool(use_openai)
        self._api_key = api_key or ""
        if model:
            self._model = model

    # ---------------- Public ----------------

    def ping(self) -> Tuple[bool, str, Optional[dict]]:
        """
        Lightweight test call to verify API key/model. Returns (ok, message, usage|None).
        Never raises out to caller.
        """
        if not (self._use_openai and self._api_key and _OPENAI_AVAILABLE):
            return False, "OpenAI is disabled or not configured.", None

        try:
            client = OpenAI(api_key=self._api_key)
            resp = client.responses.create(
                model=self._model,
                input=[{"role": "user", "content": "Reply with the single word OK."}],
                temperature=0.0,
            )
            text = _extract_text(resp).strip()
            ok = text.upper().startswith("OK")
            usage = _safe_usage_dict(resp)
            if ok:
                return True, "Round-trip succeeded.", usage
            return False, f"Unexpected response text: {text[:80]}", usage
        except Exception as e:
            return False, f"{type(e).__name__}: {e}", None

    def plan_week(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> List[WorkoutSuggestion] | Tuple[List[WorkoutSuggestion], dict]:
        """
        Return a list of WorkoutSuggestion (one per input date).
        If OpenAI path runs, returns (suggestions, usage_dict).
        """
        if self._use_openai and self._api_key and _OPENAI_AVAILABLE:
            try:
                return self._plan_with_openai(ctx, week_dates, recent_workouts)
            except Exception:
                # Fall back gracefully
                return self._plan_heuristic(ctx, week_dates, recent_workouts)
        else:
            return self._plan_heuristic(ctx, week_dates, recent_workouts)

    # --------------- Implementations ---------------

    def _plan_with_openai(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> Tuple[List[WorkoutSuggestion], dict]:
        client = OpenAI(api_key=self._api_key)

        compact_recent = [
            {
                "date": r.get("date"),
                "type": r.get("workout_type"),
                "planned_distance": r.get("planned_distance"),
                "completed": bool(r.get("completed")),
                "actual_distance": r.get("actual_distance"),
                "actual_time_seconds": r.get("actual_time_seconds"),
                "rpe": r.get("actual_rpe"),
            }
            for r in recent_workouts[-25:]
        ]

        system_msg = (
            "You are an experienced running coach. Given a training context and a list of dates (one week), "
            "produce a STRICT JSON array with 7 objects—one per date—with keys:\n"
            "date (YYYY-MM-DD), workout_type (easy|tempo|intervals|long|recovery|rest), "
            "planned_distance (miles or null), planned_intensity (string or null), description (string or null). "
            "Distances must be reasonable for recreational runners and consistent with goal_type. Prefer easier options when unsure."
        )
        user_msg = json.dumps(
            {"context": ctx.__dict__, "week_dates": week_dates, "recent_workouts": compact_recent},
            ensure_ascii=False,
        )

        resp = client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )

        text = _extract_text(resp)
        data = json.loads(text)

        suggestions: List[WorkoutSuggestion] = [
            WorkoutSuggestion(
                date=item.get("date"),
                workout_type=(item.get("workout_type") or "easy").lower(),
                planned_distance=_to_float_or_none(item.get("planned_distance")),
                planned_intensity=item.get("planned_intensity"),
                description=item.get("description"),
            )
            for item in data
        ]

        # Keep order aligned to week_dates
        by_date = {s.date: s for s in suggestions if s.date}
        ordered = [by_date.get(d) or WorkoutSuggestion(d, "rest") for d in week_dates]

        usage = _safe_usage_dict(resp)
        usage["estimated_cost_usd"] = AIPlanner._estimate_cost(
            self._model, usage.get("prompt_tokens"), usage.get("completion_tokens")
        )
        usage["model"] = self._model

        return ordered, usage

    def _plan_heuristic(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> List[WorkoutSuggestion]:
        """Very simple non-AI filler respecting long_run_day and max training days."""
        long_day = (ctx.long_run_day or "Sunday").lower()
        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # crude mileage guess from recent average
        distances: List[float] = []
        for r in recent_workouts:
            d = r.get("actual_distance") or r.get("planned_distance")
            if isinstance(d, (int, float)):
                distances.append(float(d))
        avg = sum(distances) / len(distances) if distances else 3.0

        suggestions: List[WorkoutSuggestion] = []
        used_days = 0
        for d in week_dates:
            idx = _weekday_index(d)  # 0=Mon..6=Sun
            name = weekday_names[idx]

            if name == long_day and used_days < ctx.max_days_per_week:
                used_days += 1
                suggestions.append(
                    WorkoutSuggestion(
                        date=d,
                        workout_type="long",
                        planned_distance=round(min(avg * 1.7, 12.0), 1),
                        planned_intensity="Z2-3",
                        description="Comfortable long run; keep it conversational.",
                    )
                )
                continue

            if used_days >= ctx.max_days_per_week:
                suggestions.append(WorkoutSuggestion(date=d, workout_type="rest"))
                continue

            if name in ("tuesday",):
                used_days += 1
                suggestions.append(
                    WorkoutSuggestion(
                        date=d,
                        workout_type="intervals",
                        planned_distance=round(max(avg, 3.0), 1),
                        planned_intensity="5x(3min hard / 2min easy)",
                        description="Quality intervals; warmup/cooldown included.",
                    )
                )
            elif name in ("thursday",):
                used_days += 1
                suggestions.append(
                    WorkoutSuggestion(
                        date=d,
                        workout_type="tempo",
                        planned_distance=round(max(avg, 3.5), 1),
                        planned_intensity="20–25min comfortably hard",
                        description="Steady tempo; smooth effort.",
                    )
                )
            elif name in ("saturday",):
                used_days += 1
                suggestions.append(
                    WorkoutSuggestion(
                        date=d,
                        workout_type="easy",
                        planned_distance=round(max(avg * 0.8, 2.5), 1),
                        planned_intensity="Z1-2",
                        description="Easy shakeout; relaxed form.",
                    )
                )
            else:
                suggestions.append(WorkoutSuggestion(date=d, workout_type="rest"))

        return suggestions


# ---------------- Helpers ----------------

def _weekday_index(date_str: str) -> int:
    from datetime import datetime as _dt
    return _dt.strptime(date_str, "%Y-%m-%d").weekday()  # 0=Mon..6=Sun


def _to_float_or_none(x: Any) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None


def _extract_text(resp) -> str:
    # OpenAI Responses v2 style
    try:
        if hasattr(resp, "output") and resp.output:
            for p in resp.output:
                if getattr(p, "type", None) == "message" and getattr(p, "content", None):
                    for c in p.content:
                        if getattr(c, "type", None) in ("output_text", "text"):
                            return c.text
        if hasattr(resp, "content") and resp.content:
            return str(resp.content)
    except Exception:
        pass
    return ""


def _safe_usage_dict(resp) -> dict:
    usage = getattr(resp, "usage", None)
    out = {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    if not usage:
        return out
    out["prompt_tokens"] = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    out["completion_tokens"] = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
    out["total_tokens"] = getattr(usage, "total_tokens", None)
    return out
