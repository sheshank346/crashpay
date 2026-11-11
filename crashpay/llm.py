import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
MODEL = "openai/gpt-oss-120b"


def ask(prompt):
    for attempt in range(4):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))