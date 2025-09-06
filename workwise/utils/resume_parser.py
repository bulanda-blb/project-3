import re
import json
import openai
from openai import OpenAI
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY
client = OpenAI(api_key=settings.OPENAI_API_KEY)

PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "name":        {"type": ["string", "null"]},
        "email":       {"type": ["string", "null"]},
        "phone":       {"type": ["string", "null"]},
        "address":     {"type": ["string", "null"]},
        "summary":     {"type": ["string", "null"]},
        "education":   {"type": "array", "items": {"type": "string"}},
        "experience":  {"type": "array", "items": {"type": "string"}},
        "skills":      {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
        "languages":   {"type": "array", "items": {"type": "string"}},
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":        {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]}
                }
            }
        },
        "hobbies":     {"type": "array", "items": {"type": "string"}},
        "achievements":{"type": "array", "items": {"type": "string"}}
    },
    "required": ["name","email"]
}

def fix_newlines(obj):
    if isinstance(obj, str):
        # Convert literal backslash-n sequences into real newlines
        return obj.replace('\\n', '\n')
    elif isinstance(obj, list):
        return [fix_newlines(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: fix_newlines(val) for key, val in obj.items()}
    else:
        return obj

def parse_resume(text: str) -> dict:
    
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
              "role": "system",
              "content": "You are a resume parser. Extract structured data per the schema."
            },
            {
              "role": "user",
              "content": text
            }
        ],
        functions=[{
            "name": "extract_resume_data",
            "description": "Parse resume into JSON",
            "parameters": PARSE_SCHEMA
        }],
        function_call={"name": "extract_resume_data"},
        temperature=0
    )

    raw = resp.choices[0].message.function_call.arguments  
    # Clean any stray backticks or whitespace
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    data = fix_newlines(data)

    return data
