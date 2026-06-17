from dotenv import load_dotenv
import anthropic

load_dotenv()

lead = {
    "name": "Sarah Johnson",
    "business_name": "Bloom Bakery",
    "inquiry": "custom wedding cake packages and pricing",
}

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    system=(
        "You are a helpful sales assistant. Write short, warm, and professional "
        "follow-up emails for leads who have inquired about our services. "
        "Keep emails under 150 words. Do not use placeholders — write the full email."
    ),
    messages=[
        {
            "role": "user",
            "content": (
                f"Write a follow-up email for this lead:\n"
                f"Name: {lead['name']}\n"
                f"Business: {lead['business_name']}\n"
                f"They inquired about: {lead['inquiry']}"
            ),
        }
    ],
)

print(response.content[0].text)
