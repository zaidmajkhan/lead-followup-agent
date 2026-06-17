# Lead Follow-Up Agent

An AI-powered email generator that turns lead info into personalized follow-up emails. Provide a lead's name, business, and inquiry topic — the Claude API handles the rest and prints a ready-to-send email to the terminal.

## Tech Stack

- Python 3
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (`claude-sonnet-4-6`)
- `python-dotenv`

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/lead-followup-agent.git
   cd lead-followup-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your API key**

   Create a `.env` file in the project root:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```
   Get a key at [console.anthropic.com](https://console.anthropic.com).

4. **Run**
   ```bash
   python main.py
   ```

## Example Output

Given this lead in `main.py`:

```python
lead = {
    "name": "James Carter",
    "business_name": "Carter Auto Group",
    "inquiry": "fleet vehicle pricing and bulk purchase discounts",
}
```

The script prints:

```
Subject: Following Up — Fleet Pricing for Carter Auto Group

Hi James,

Thanks for your interest in our fleet vehicle program! We work with a number
of local businesses and can offer competitive bulk pricing that scales with
your order size.

I'd love to set up a quick call to learn more about your needs — fleet size,
preferred makes/models, and timeline — so I can put together a tailored quote
for Carter Auto Group.

Would any time this week work for you?

Best,
[Your Name]
```

## Customization

Edit the `lead` dict at the top of `main.py` to generate emails for different contacts.
