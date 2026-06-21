# Lead Follow-Up Agent

An AI-powered tool that turns lead info into personalized follow-up emails and sends them through Gmail. Add your leads to a JSON file — the Claude API drafts a warm, polished email for each one, and the agent delivers them (or previews them with `--dry-run`).

## Features

- Personalized email generation with the Anthropic Claude API
- Gmail delivery via the official Gmail API (OAuth)
- `--dry-run` mode to preview emails without sending
- Leads loaded from a JSON file — no code edits needed
- Sent-tracking to avoid contacting the same lead twice
- Configurable model, signature, company name, and send delay
- Structured logging and per-lead error handling (one failure won't stop the run)

## Tech Stack

- Python 3.10+
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (default model `claude-sonnet-4-6`)
- Gmail API via `google-api-python-client` + `google-auth-oauthlib`
- `python-dotenv`

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/lead-followup-agent.git
cd lead-followup-agent
pip install -r requirements.txt
```

### 2. Add your Anthropic API key

Copy `.env.example` to `.env` and fill in your key (get one at [console.anthropic.com](https://console.anthropic.com)):

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Set up Gmail access

> Skip this step if you only plan to use `--dry-run`.

1. In the [Google Cloud Console](https://console.cloud.google.com), create a project and enable the **Gmail API**.
2. Configure an **OAuth consent screen** (External is fine for personal use; add your own email as a test user).
3. Create an **OAuth client ID** of type **Desktop app** and download the JSON.
4. Save it in the project root as `credentials.json`.

On the first live run, a browser window opens for you to authorize access. A `token.json` is then cached so you won't be prompted again.

### 4. Add your leads

Copy the example and edit it:

```bash
cp leads.example.json leads.json
```

Each lead needs four fields:

```json
[
  {
    "name": "Sarah Johnson",
    "business_name": "Bloom Bakery",
    "email": "sarah@example.com",
    "inquiry": "custom wedding cake packages and pricing"
  }
]
```

## Usage

Preview emails without sending (recommended first):

```bash
python main.py --dry-run
```

Send for real:

```bash
python main.py
```

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--leads` | `leads.json` | Path to the leads JSON file |
| `--dry-run` | off | Generate and print emails without sending |
| `--model` | `claude-sonnet-4-6` | Claude model to use |
| `--delay` | `1.0` | Seconds to wait between sends |
| `--sent-log` | `sent.json` | Path to the sent-tracking file |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

### Configuration (`.env`)

| Variable | Default | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `MODEL` | `claude-sonnet-4-6` | Claude model |
| `MAX_TOKENS` | `512` | Max tokens per generated email |
| `SIGNATURE_NAME` | `The Team` | Sign-off used at the end of every email |
| `COMPANY_NAME` | _(empty)_ | Optional company name shown in the subject line |
| `SEND_DELAY_SECONDS` | `1.0` | Delay between sends |

## Example output (`--dry-run`)

```
======================================================================
To: sarah@example.com
Subject: Following up – Bloom Bakery
----------------------------------------------------------------------
Hi Sarah,

Thank you for reaching out about custom wedding cake packages! We'd love
to help make your celebration unforgettable with a design tailored to
your theme, guest count, and budget.

I'd be happy to walk you through our package options and pricing on a
quick call this week. When works best for you?

Warm regards,
The Team
```

## Development

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and [black](https://black.readthedocs.io/) for formatting:

```bash
pip install ruff black
ruff check .
black .
```

Linting runs automatically on push via GitHub Actions (`.github/workflows/lint.yml`).

## Notes on data & privacy

`leads.json`, `sent.json`, `.env`, `credentials.json`, and `token.json` are all git-ignored so customer data and secrets never get committed.

## License

[MIT](LICENSE)
