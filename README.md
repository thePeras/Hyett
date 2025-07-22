# Hyett

Hyett is a simple script to automate the process of software development using LLM tool by completely replace the human code intervention. Just assign an issue to Hyett and it will take care of the rest: writing code, committing it, and creating the pull request. 

The pull request is not perfect? Request changes on the PR just like a human and Hyett will attend your needs.

It runs locally, for now.

Note:
> Gemini 2.5 is f*cking powerful to do boring software. With simple requests and a good repo context, it will certainly produce the intended code.

## To run the Hyett locally:

- Make sure all dependencies are installed and the .env file is correct
- Start ngrok: ```ngrok http 8000```
- Update the webhook URL in your GitHub repository settings to point to the ngrok URL followed by `/webhook`
- Start the FastAPI server: ```uvicorn main:app```

Now, create a new issue and assign yourself to it.
Watch the console output and grab a coffee while the bot does your work!