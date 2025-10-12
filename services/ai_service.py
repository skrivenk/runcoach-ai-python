from openai import OpenAI
from typing import Dict, Any
import json


class AIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_training_plan(self, params: Dict[str, Any]) -> Dict:
        """Generate training plan using OpenAI"""

        prompt = f"""
        Create a {params['duration_weeks']}-week training plan for {params['goal']}.

        Baseline: {params['baseline_distance']} miles in {params['baseline_time']} minutes
        Max days per week: {params['max_days_per_week']}
        Long run day: {params['long_run_day']}

        Return JSON with structure:
        {{
            "weeks": [
                {{
                    "week": 1,
                    "total_mileage": 25,
                    "days": [
                        {{
                            "day": 1,
                            "type": "easy|tempo|intervals|long|recovery|rest",
                            "distance": 5.0,
                            "description": "Detailed instructions"
                        }}
                    ]
                }}
            ]
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert running coach."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)