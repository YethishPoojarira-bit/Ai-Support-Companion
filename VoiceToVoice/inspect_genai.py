import asyncio
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    # Use the model that definitely exists from previous `pip list` or `models.list()` check
    # gemini-2.0-flash-exp was in the list.
    model = "gemini-2.0-flash-exp" 
    try:
        async with client.aio.live.connect(model=model, config={}) as session:
            print("Session Type:", type(session))
            print("Attributes:", [d for d in dir(session) if not d.startswith('_')])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
