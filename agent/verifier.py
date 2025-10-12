import re
import json
from typing import Dict


def parse_answer(response: str) -> Dict[str, str]:
    # 1) pull out what's inside the tags (if present), else use full string
    m = re.search(r"<answer>\s*(.*?)\s*</answer>", response)
    content = m.group(1) if m else response.strip()

    # 2) strip parentheses
    content = content.strip()
    if content.startswith("(") and content.endswith(")"):
        content = content[1:-1]

    # 3) split into parts and build dict
    parts = [p.strip() for p in content.split(",") if p.strip()]
    result: Dict[str, str] = {}
    for part in parts:
        # match a sign (+, -, or 0) followed by an axis letter
        mm = re.match(r"^([+\-0])([XYZ])$", part)
        if mm:
            sign, axis = mm.groups()
            result[axis] = sign
    return result


def parse_answer_json(llm_response: str) -> dict:
    # Extract content between <answer> and </answer>
    match = re.search(r'<answer>(.*?)</answer>', llm_response, re.DOTALL)

    if not match:
        raise ValueError("No <answer>...</answer> tags found in response")

    answer_content = match.group(1).strip()

    try:
        # Parse the JSON string into a dictionary
        return json.loads(answer_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in answer tags: {e}")


def check_answer(groundtruth: str, response: str) -> bool:
    # parse both into dicts
    parsed = parse_answer(response)
    gt = parse_answer(groundtruth)

    # verify each axis in the parsed answer matches groundtruth
    for axis, sign in parsed.items():
        if gt.get(axis) != sign:
            return False
    return True
