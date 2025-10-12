import os
import base64
import mimetypes
from openai import OpenAI
from typing import List, Dict

# instantiate once
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(
    messages: List[Dict[str, str]],
    model_name: str = "gpt-4o",
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def local_image_to_data_url(image_path: str) -> str:
    """
    Convert a local image file to a base64-encoded data URL.
    """
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "application/octet-stream"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def call_vlm(
    messages: List[Dict[str, str]],
    image_path: str,
    model_name: str = "gpt-4o",
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    # convert image → data URL
    data_url = local_image_to_data_url(image_path)

    # locate last user message
    last_user_idx = max(i for i, m in enumerate(messages) if m["role"] == "user")

    # build new messages list with the image embedded
    new_msgs: List[Dict] = []
    for i, m in enumerate(messages):
        if i == last_user_idx:
            new_msgs.append({
                "role": "user",
                "content": [
                    {"type": "text",      "text": m["content"]},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            })
        else:
            new_msgs.append(m)

    resp = client.chat.completions.create(
        model=model_name,
        messages=new_msgs,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()