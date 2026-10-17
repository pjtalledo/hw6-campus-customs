# HOMEWORK 6 PROJECT RULES

These rules apply only to the Homework 6 project folder and override the
parent `MGT 409 AI` instructions for this project. Other lectures/homeworks
are unaffected.

## OPENAI AND PORTKEY

- Use only `gpt-6-luna` for AI model calls (required by the professor for
  Homework 6).
- Read the API key from `PORTKEY_API_KEY` in the root `.env` file.
- Never hard-code, print, commit, or expose API keys or secrets.

## PROJECT ENVIRONMENTS

- This project folder must contain its own `.venv` Python virtual
  environment.
- Keep dependencies in `requirements.txt` in this folder.

## SAFETY RULES

- Never send real emails or make real payments.
- Do not implement future problems before instructions for them are given.
- Keep `AI_prompts.md` accurate and updated as we work.

## VISUAL ASSETS

- Create Labubus and other creatures as HTML/CSS, not image generation.
- Websites must use a black-and-pink theme.

## DASH RUN RULES

- Disable Dash's auto-reloader and prefer `debug=False`.
- Do not start multiple development servers for one app.
- When stopping an app, terminate the entire process tree, not only the
  process on port 8050.
