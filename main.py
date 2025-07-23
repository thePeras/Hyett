import os
import hmac
import hashlib

from configs import MY_USERNAME, GITHUB_WEBHOOK_SECRET
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from workflows.issue_assign import handle_issue_assigned
from workflows.pr_review import handle_pr_review

app = FastAPI()

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            raise HTTPException(status_code=403, detail="X-Hub-Signature-256 header is missing!")

        body = await request.body()
        hash_object = hmac.new(GITHUB_WEBHOOK_SECRET, msg=body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            raise HTTPException(status_code=403, detail="Request signature does not match!")

        return {"status": "ok", "event_received": "webhook received"}

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

            is_my_pr = pr.get("user", {}).get("login") == MY_USERNAME
            is_change_request = review.get("state") == "changes_requested"
            request_from_owner = review.get("user", {}).get("login") == MY_USERNAME
            
            if not (is_my_pr and is_change_request and request_from_owner):
                return

            print("2 - ✅ A PR review received. Let's handle it!")
            background_tasks.add_task(handle_pr_review, payload)

        return {"status": "ok", "event_received": event}
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

