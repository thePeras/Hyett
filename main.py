from configs import MY_USERNAME
import os
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from workflows.issue_assign import handle_issue_assigned
from workflows.pr_review import handle_pr_review

app = FastAPI()

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        # TODO: Request signature verification

        # Handle the webhook event
        payload = await request.json()
        event = request.headers.get('X-GitHub-Event')

        if event == "issues" and payload.get("action") == "assigned":
            if payload.get("assignee", {}).get("login") != MY_USERNAME:
                return

            print("1 - ✅ I have been assigned to an issue. Let's work baby!")
            background_tasks.add_task(handle_issue_assigned, payload)

        if event == "pull_request_review" and payload.get("action") == "submitted":
            review = payload["review"]
            pr = payload["pull_request"]

            # TODO: check if the owner of the PR is the bot
            if not (review["state"] == "changes_requested" and review["user"]["login"] == MY_USERNAME):
                return

            print("2 - ✅ PR review submitted. Let's handle it!")
            background_tasks.add_task(handle_pr_review, payload)

        return {"status": "ok", "event_received": event}
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

