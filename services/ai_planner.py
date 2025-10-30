# services/ai_planner.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# OpenAI is optional; import defensively so the app still runs without it.
_OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # SDK v1.x
    _OPENAI_AVAILABLE = True
except Exception:
    pass


# ---- rough/adjustable pricing (USD per 1M tokens) ----
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Adjust to whatever model/pricing you actually use
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.30, "output": 1.20},
}


def _estimate_cost(model: str, prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> Optional[float]:
    try:
        p = _MODEL_PRICING.get((model or "").lower())
        if not p or prompt_tokens is None or completion_tokens is None:
            return None
        return (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000.0
    except Exception:
        return None


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
    Facade the calendar uses. If OpenAI is enabled + key present, we call the API.
    Otherwise we fall back to a deterministic heuristic.
    """

    def __init__(self, use_openai: bool = False, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self._use_openai = bool(use_openai)
        self._api_key = api_key or ""
        self._model = model

    def set_config(self, use_openai: bool, api_key: Optional[str], model: Optional[str] = None):
        self._use_openai = bool(use_openai)
        self._api_key = api_key or ""
        if model:
            self._model = model

    # ---------------------- public ----------------------

    def plan_week(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> Tuple[List[WorkoutSuggestion], Dict[str, Any]]:
        """
        Returns (suggestions, usage_dict).
        suggestions: list[WorkoutSuggestion] (7 items; 'rest' allowed)
        usage_dict:  {'prompt_tokens','completion_tokens','total_tokens','estimated_cost_usd','model'}
        """
        if self._use_openai and self._api_key and _OPENAI_AVAILABLE:
            try:
                return self._plan_with_openai(ctx, week_dates, recent_workouts)
            except Exception:
                # Fall back gracefully if the API call fails
                return self._plan_heuristic(ctx, week_dates, recent_workouts)
        else:
            return self._plan_heuristic(ctx, week_dates, recent_workouts)

    # ---------------------- implementations ----------------------

    def _plan_with_openai(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> Tuple[List[WorkoutSuggestion], Dict[str, Any]]:
        """
        Calls OpenAI Responses API and expects strict JSON back.
        """
        client = OpenAI(api_key=self._api_key)

        # Compact the recent list so we don’t blow up token usage
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
            "You are an experienced running coach. "
            "Given a training context and a list of dates (one week), create a simple plan. "
            "Output STRICT JSON: an array with 7 objects, one per input date, each with keys: "
            "date (YYYY-MM-DD), workout_type (easy|tempo|intervals|long|recovery|rest), "
            "planned_distance (miles, number or null), planned_intensity (string or null), description (string or null). "
            "Distances must be reasonable for recreational runners and consistent with goal_type. "
            "Use 'rest' for days off. If unsure, prefer easier options."
        )

        user_msg = json.dumps(
            {
                "context": ctx.__dict__,
                "week_dates": week_dates,
                "recent_workouts": compact_recent,
            },
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

        # ---- parse content ----
        text = _extract_text(resp)
        data = json.loads(text)

        suggestions: List[WorkoutSuggestion] = []
        for item in data:
            suggestions.append(
                WorkoutSuggestion(
                    date=item.get("date"),
                    workout_type=(item.get("workout_type") or "easy").lower(),
                    planned_distance=_to_float_or_none(item.get("planned_distance")),
                    planned_intensity=item.get("planned_intensity"),
                    description=item.get("description"),
                )
            )

        # Preserve order of the incoming week_dates (fill with 'rest' if missing)
        by_date = {s.date: s for s in suggestions if s.date}
        ordered = [by_date.get(d) or WorkoutSuggestion(d, "rest") for d in week_dates]

        # ---- usage/cost ----
        prompt_toks = None
        completion_toks = None
        total_toks = None
        try:
            usage = getattr(resp, "usage", None)
            if usage:
                prompt_toks = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
                completion_toks = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
                total_toks = getattr(usage, "total_tokens", None)
        except Exception:
            pass

        return ordered, {
            "prompt_tokens": prompt_toks,
            "completion_tokens": completion_toks,
            "total_tokens": total_toks,
            "estimated_cost_usd": _estimate_cost(self._model, prompt_toks, completion_toks),
            "model": self._model,
        }

    def _plan_heuristic(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> Tuple[List[WorkoutSuggestion], Dict[str, Any]]:
        """
        Very simple non-AI filler that respects long_run_day and max training days.
        """
        long_day = (ctx.long_run_day or "Sunday").lower()
        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # Crude mileage guess from recent average
        distances = []
        for r in recent_workouts:
            d = r.get("actual_distance") or r.get("planned_distance")
            if isinstance(d, (int, float)):
                distances.append(float(d))
        avg = sum(distances) / len(distances) if distances else 3.0

        suggestions: List[WorkoutSuggestion] = []
        used_days = 0
        for d in week_dates:
            idx = _weekday_index(d)  # 0=Mon ... 6=Sun
            name = weekday_names[idx]

            # Long run
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

            # Cap by max days/week
            if used_days >= ctx.max_days_per_week:
                suggestions.append(WorkoutSuggestion(date=d, workout_type="rest"))
                continue

            # Simple weekly pattern
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

        return suggestions, {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "estimated_cost_usd": None,
            "model": "heuristic",
        }


# ---------------------- helpers ----------------------

def _weekday_index(date_str: str) -> int:
    from datetime import datetime as _dt
    dt = _dt.strptime(date_str, "%Y-%m-%d")
    return dt.weekday()  # 0=Mon ... 6=Sun


def _to_float_or_none(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _extract_text(resp) -> str:
    """
    Extract text safely from OpenAI Responses API result (SDK v1).
    We look through the top-level output message parts for a text chunk.
    """
    # Preferred shape: resp.output[*].content[*].text
    try:
        parts = getattr(resp, "output", None)
        if parts:
            for p in parts:
                if getattr(p, "type", None) == "message" and getattr(p, "content", None):
                    for c in p.content:
                        # response object uses "type": "output_text" for text content
                        if getattr(c, "type", None) in ("output_text", "text") and hasattr(c, "text"):
                            return c.text
    except Exception:
        pass

    # Fallbacks
    if hasattr(resp, "content") and resp.content:
        return str(resp.content)
    return ""
