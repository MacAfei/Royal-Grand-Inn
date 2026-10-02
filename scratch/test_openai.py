import os
import openai
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
print("Key length:", len(key) if key else 0)
print("Key prefix:", key[:10] if key else "None")

client = openai.OpenAI(api_key=key)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello!"}],
        max_tokens=10
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error calling OpenAI:", e)
