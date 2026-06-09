import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

from services.llm_client import chat, get_model

print(f"Model: {get_model()}")
print(chat("Reply with just: OpenRouter working", max_tokens=20))
