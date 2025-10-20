# services/ai_planner.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class PlanContext:
    id: int
    name: str
    goal_type: str
    start_date: str
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
    planned_distance: Optional[float]
    planned_intensity: Optional[str]
    description: Optional[str]


WEEKDAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class AIPlanner:
    def __init__(self):
        self._use_openai = False
        self._openai = None
        key = os.getenv("OPENAI_API_KEY")
        if key:
            try:
                import openai  # type: ignore
                self._openai = openai
                self._openai.api_key = key
                self._use_openai = False  # flip to True later if you want live calls
            except Exception:
                self._openai = None
                self._use_openai = False

    def plan_week(self, plan: PlanContext, week_dates: List[str], recent_workouts: List[Dict]) -> List[WorkoutSuggestion]:
        if self._use_openai and self._openai:
            try:
                return self._plan_week_with_openai(plan, week_dates, recent_workouts)
            except Exception:
                pass
        return self._plan_week_heuristic(plan, week_dates, recent_workouts)

    def _plan_week_heuristic(self, plan: PlanContext, week_dates: List[str], recent_workouts: List[Dict]) -> List[WorkoutSuggestion]:
        try:
            sd = datetime.fromisoformat(plan.start_date).date()
            wd0 = datetime.fromisoformat(week_dates[0]).date()
            weeks_into = max(0, (wd0 - sd).days // 7)
        except Exception:
            weeks_into = 0

        base_easy = {"general": 4.0, "5k": 3.5, "10k": 4.5, "half": 5.0, "marathon": 6.0}.get(plan.goal_type, 4.0)
        base_long = {"general": 7.0, "5k": 6.0, "10k": 8.0, "half": 10.0, "marathon": 12.0}.get(plan.goal_type, 8.0)
        base_tempo = {"general": 4.0, "5k": 3.5, "10k": 4.5, "half": 5.5, "marathon": 6.0}.get(plan.goal_type, 5.0)
        base_intervals = {"general": 3.5, "5k": 3.0, "10k": 4.0, "half": 4.5, "marathon": 5.0}.get(plan.goal_type, 4.0)

        prog = min(1.0 + weeks_into * plan.weekly_increase_cap, 1.0 + plan.long_run_cap)

        easy_mi = round(base_easy * prog, 1)
        tempo_mi = round(base_tempo * prog, 1)
        ints_mi = round(base_intervals * prog, 1)
        long_mi = round(base_long * min(1.0 + weeks_into * (plan.weekly_increase_cap * 0.7), 1.0 + plan.long_run_cap), 1)

        run_days = self._pick_run_days(plan.max_days_per_week, plan.long_run_day)
        tempo_day = self._shift_day(plan.long_run_day, -3)
        intervals_day = self._shift_day(plan.long_run_day, -1)

        out: List[WorkoutSuggestion] = []
        for i, d in enumerate(week_dates):
            weekday = WEEKDAY_ORDER[i]
            if weekday == plan.long_run_day and weekday in run_days:
                out.append(WorkoutSuggestion(d, "long", long_mi, None, "Long run"))
            elif weekday == tempo_day and weekday in run_days:
                out.append(WorkoutSuggestion(d, "tempo", tempo_mi, "T pace", "Tempo run"))
            elif weekday == intervals_day and weekday in run_days:
                out.append(WorkoutSuggestion(d, "intervals", ints_mi, "I pace", "Intervals"))
            elif weekday in run_days:
                out.append(WorkoutSuggestion(d, "easy", easy_mi, None, "Easy run"))
            else:
                out.append(WorkoutSuggestion(d, "rest", None, None, "Rest / cross-train"))
        return out

    def _pick_run_days(self, max_days: int, long_run_day: str) -> List[str]:
        pattern = ["Tuesday", "Thursday", "Saturday"] if long_run_day in ("Sunday",) else ["Monday", "Wednesday", "Friday"]
        chosen = set([long_run_day])
        for d in pattern:
            if len(chosen) >= max_days:
                break
            chosen.add(d)
        for d in WEEKDAY_ORDER:
            if len(chosen) >= max_days:
                break
            if d not in chosen and d not in ("Sunday", "Saturday", long_run_day):
                chosen.add(d)
        return [d for d in WEEKDAY_ORDER if d in chosen]

    def _shift_day(self, day: str, offset: int) -> str:
        idx = WEEKDAY_ORDER.index(day)
        return WEEKDAY_ORDER[(idx + offset) % 7]

    def _plan_week_with_openai(self, plan: PlanContext, week_dates: List[str], recent_workouts: List[Dict]) -> List[WorkoutSuggestion]:
        # Placeholder for a real OpenAI call — keeping heuristic for now
        return self._plan_week_heuristic(plan, week_dates, recent_workouts)
