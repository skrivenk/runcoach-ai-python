# services/ai_planner.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# OpenAI is optional; we import lazily to avoid hard dependency at runtime
_OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # SDK v1.x+
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
    Facade the calendar uses. If OpenAI is enabled + key present, we call the API.
    Otherwise we fall back to a deterministic heuristic.
    """

    _MODEL_PRICING = {
        # Rough placeholders (USD per 1M tokens). Adjust if you have contract pricing.
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4.1-mini": {"input": 0.30, "output": 1.20},
    }

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

    def ping(self) -> Tuple[bool, str, Optional[dict]]:
        """
        Quick health check of OpenAI creds/model. Returns (ok, message, usage_dict?)
        """
        if not (self._use_openai and self._api_key and _OPENAI_AVAILABLE):
            return False, "OpenAI disabled or key not set (or SDK missing).", None
        try:
            client = OpenAI(api_key=self._api_key)
            resp = client.responses.create(
                model=self._model,
                input=[{"role": "user", "content": "Reply with: ok"}],
                temperature=0.0,
            )
            text = _extract_text(resp).strip().lower()
            usage = _extract_usage(self._model, resp)
            return ("ok" in text, f"Model replied: {text!r}", usage)
        except Exception as e:
            return False, f"Error: {e}", None

    def plan_week(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> List[WorkoutSuggestion] | Tuple[List[WorkoutSuggestion], dict]:
        """
        Return WorkoutSuggestion list (one per day; 'rest' allowed).
        When using OpenAI, returns (suggestions, usage_dict).
        Heuristic returns just suggestions list.
        """
        if self._use_openai and self._api_key and _OPENAI_AVAILABLE:
            try:
                return self._plan_with_openai(ctx, week_dates, recent_workouts)
            except Exception:
                return self._plan_heuristic(ctx, week_dates, recent_workouts)
        else:
            return self._plan_heuristic(ctx, week_dates, recent_workouts)

    def weekly_insight(
        self,
        ctx: PlanContext,
        stats: Dict[str, Any],
        recent_workouts: List[Dict[str, Any]],
    ) -> Tuple[str, Optional[dict]]:
        """
        Produce a short coaching insight for the last 7 days.
        Returns (insight_text, usage_dict or None for heuristic).
        """
        if self._use_openai and self._api_key and _OPENAI_AVAILABLE:
            try:
                client = OpenAI(api_key=self._api_key)
                # Compact the recent list
                compact_recent = [
                    {
                        "date": r.get("date"),
                        "type": r.get("workout_type"),
                        "planned_distance": r.get("planned_distance"),
                        "completed": bool(r.get("completed")),
                        "actual_distance": r.get("actual_distance"),
                        "rpe": r.get("actual_rpe"),
                    }
                    for r in recent_workouts[-25:]
                ]
                system_msg = (
                    "You are an experienced running coach. Based on the athlete's last 7 days of training "
                    "and plan context, give a concise, motivational insight (3–6 sentences). "
                    "Offer 1–2 concrete suggestions for the upcoming week. Avoid emojis."
                )
                user_payload = {
                    "plan_context": ctx.__dict__,
                    "week_stats": stats,
                    "recent_workouts": compact_recent,
                }
                resp = client.responses.create(
                    model=self._model,
                    input=[{"role": "system", "content": system_msg},
                           {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
                    temperature=0.7,
                )
                text = _extract_text(resp).strip()
                usage = _extract_usage(self._model, resp)
                return text, usage
            except Exception:
                pass

        # Heuristic fallback
        planned = float(stats.get("planned", 0.0) or 0.0)
        actual = float(stats.get("actual", 0.0) or 0.0)
        completed = int(stats.get("completed_count", 0) or 0)
        total = int(stats.get("total_count", 0) or 0)
        pct = (actual / planned * 100.0) if planned > 0 else 0.0
        goal = (ctx.goal_type or "general").lower()
        advice = "Nice consistency. Keep your easy days truly easy and fuel well before quality sessions."
        if pct >= 85:
            note = "You're on track this week."
        elif pct >= 60:
            note = "You're getting there—consider a slightly shorter long run and a bit more recovery."
        else:
            note = "Dial it back and rebuild consistency with shorter easy runs and one quality day."
        if goal in ("half marathon", "marathon"):
            advice += " Add 5–10 minutes to your long-run easy portion if you feel good."
        elif goal in ("10k", "5k"):
            advice += " Consider short strides after easy runs (4–6×20 seconds fast with full recovery)."
        insight = (
            f"Last 7 days: {actual:.1f}/{planned:.1f} mi planned, "
            f"{completed}/{total} workouts completed. {note} {advice}"
        )
        return insight, None

    # ---------------------- implementations ----------------------

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
            "You are an experienced running coach. "
            "Given a training context and a list of dates (one week), create a simple plan. "
            "Output STRICT JSON: an array with 7 objects, one per input date, each with keys: "
            "date (YYYY-MM-DD), workout_type (easy|tempo|intervals|long|recovery|rest), "
            "planned_distance (miles, number or null), planned_intensity (string or null), description (string or null). "
            "Distances must be reasonable and consistent with goal_type. Prefer easier options if unsure."
        )

        user_msg = json.dumps(
            {"context": ctx.__dict__, "week_dates": week_dates, "recent_workouts": compact_recent},
            ensure_ascii=False,
        )

        resp = client.responses.create(
            model=self._model,
            input=[{"role": "system", "content": system_msg},
                   {"role": "user", "content": user_msg}],
            temperature=0.7,
        )

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

        by_date = {s.date: s for s in suggestions if s.date}
        ordered = [by_date.get(d) or WorkoutSuggestion(d, "rest") for d in week_dates]
        usage = _extract_usage(self._model, resp)
        return ordered, usage

    def _plan_heuristic(
        self,
        ctx: PlanContext,
        week_dates: List[str],
        recent_workouts: List[Dict[str, Any]],
    ) -> List[WorkoutSuggestion]:
        long_day = (ctx.long_run_day or "Sunday").lower()
        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

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
    Extract text safely from OpenAI Responses API result.
    """
    # SDK v1 'responses' output
    if hasattr(resp, "output") and resp.output:
        for p in resp.output:
            if getattr(p, "type", None) == "message" and getattr(p, "content", None):
                for c in p.content:
                    if getattr(c, "type", None) == "output_text":
                        return c.text or ""
    if hasattr(resp, "content") and resp.content:
        return str(resp.content)
    return ""


def _estimate_cost(model: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    try:
        pricing = AIPlanner._MODEL_PRICING.get((model or "").lower())
        if not pricing or prompt_tokens is None or completion_tokens is None:
            return None
        return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000.0
    except Exception:
        return None


def _extract_usage(model: str, resp) -> dict:
    prompt_toks = completion_toks = total_toks = None
    try:
        usage = getattr(resp, "usage", None)
        if usage:
            prompt_toks = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
            completion_toks = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
            total_toks = getattr(usage, "total_tokens", None)
    except Exception:
        pass
    return {
        "prompt_tokens": prompt_toks,
        "completion_tokens": completion_toks,
        "total_tokens": total_toks,
        "estimated_cost_usd": _estimate_cost(model, prompt_toks, completion_toks),
        "model": model,
    }
