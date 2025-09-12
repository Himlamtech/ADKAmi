# def main():
#     print("Hello from designapi!")


# if __name__ == "__main__":
#     main()

from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()
start_time = datetime.now()
response = client.chat.completions.create(
    model="gpt-4.1-nano-2025-04-14",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
)
end_time = datetime.now()
print(f"Time taken: {end_time - start_time} seconds")
print(response.choices[0].message.content)
