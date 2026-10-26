import re

from crashpay.llm import ask

PROMPT = """You are a payments security engineer. A test attack against a demo shop succeeded.

Attack: {attack}
Result: {detail}

Shop code:
{source}

In two sentences, explain the root cause. Then give the corrected version of the whole file in one python code block."""


def suggest_fix(attack, detail, source):
    return ask(PROMPT.format(attack=attack, detail=detail, source=source))


def extract_code(text):
    match = re.search(r"```python\n(.*?)```", text, re.S)
    return match.group(1) if match else None


def fix_shop(attack, detail, path="crashpay/shop.py", out="crashpay/patched_shop.py"):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    code = extract_code(suggest_fix(attack, detail, source))
    if code:
        with open(out, "w", encoding="utf-8") as f:
            f.write(code)
    return code is not None