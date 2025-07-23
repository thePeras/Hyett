# Hyett

Hyett automate the process of software development using LLM tools by completely replacing the human code intervention. Just assign an issue to Hyett and it will take care of the rest: writing code, committing it, and creating the pull request. 

If the pull request is not perfect you just need to request changes on the PR and Hyett will attend your needs.

It runs locally, for now.

Note:
> Gemini 2.5 is f*cking powerful to do boring software. With simple requests and a good repo context, it will certainly produce the intended code.

## Setup

- Install the dependencies: `pip install -r requirements.txt` #requirements.txt to be created...
- Genereate a GitHub token (Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> Generate new token) with the following scopes:
    - `Issues:read`
    - `Contents:read_and_write`
    - `Pull Requests:read_and_write`
- Set up a GitHub webhook for your repository: (Settings -> Webhooks -> Add webhook)
    - Set the "Payload URL" to `http://your_ngrok_url/webhook` (or a Cloudflare tunnel URL)
    - Set the "Content type" to `application/json`
    - Set the "Secret" to the value of `GITHUB_WEBHOOK_SECRET`
        - You can generate a one with: `openssl rand -hex 32`
    - Select the events:
        - `Issues`
        - `Pull request reviews`
        - `Pull request review comments`
- Create a GEMINI_API_KEY from [Google AI Studio](https://aistudio.google.com)
- Make sure all dependencies are installed and the .env file is correct

## To run the Hyett locally:

- Start the FastAPI server: ```uvicorn main:app```

If no Cloudflare tunnel is set up, you can use ngrok to expose your local server to the internet:
- Start ngrok: ```ngrok http 8000```
- Update the webhook URL in your GitHub repository settings to point to the ngrok URL followed by `/webhook`

Now, create a new issue and assign yourself to it.
Watch the console output and grab a coffee while the bot does your work!