import os
import sys
import base64
from openai import OpenAI

# 1. Chatbot AI (DeepSeek)
CHAT_API_KEY = "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"
CHAT_MODEL = "deepseek-ai/deepseek-v4-flash-0731"

# 2. Visual Image Processing (Nemotron Parse 2.0)
VISION_API_KEY = "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"
VISION_MODEL = "nvidia/nemotron-parse-2.0"

def test_vision():
    print("Testing Vision Model (nvidia/nemotron-parse-2.0)...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=VISION_API_KEY,
        timeout=60.0
    )
    
    messages = [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://assets.ngc.nvidia.com/products/api-catalog/nemoretriever-parse/example_1.jpg"
            }
          }
        ]
      }
    ]

    try:
        completion = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=0,
            top_p=1,
            max_tokens=1024,
            stream=False
        )
        content = completion.choices[0].message.content
        print("\n--- VISION OUTPUT (First 500 chars) ---")
        print(content[:500])
        print(f"\nTotal output length: {len(content)}")
        return True
    except Exception as e:
        print(f"Vision error: {e}")
        return False

def test_chat():
    print("\nTesting Chatbot Model (deepseek-ai/deepseek-v4-flash-0731)...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=CHAT_API_KEY,
        timeout=60.0
    )
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role":"user","content":"Write a short one-line poem about satellites."}],
            temperature=1,
            top_p=0.95,
            max_tokens=1024,
            extra_body={"chat_template_kwargs":{"thinking":True,"reasoning_effort":"high"}},
            stream=False
        )
        reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
        if reasoning:
            print("\n--- DEEPSEEK REASONING ---")
            print(reasoning[:300])
        content = completion.choices[0].message.content
        print("\n--- DEEPSEEK CONTENT ---")
        print(content)
        return True
    except Exception as e:
        print(f"Chat error: {e}")
        return False

if __name__ == "__main__":
    v_ok = test_vision()
    c_ok = test_chat()
    print(f"\nResults -> Vision: {v_ok}, Chat: {c_ok}")
