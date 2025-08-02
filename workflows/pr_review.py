import os
import requests
import git

from configs import gemini_model, flash_model, WORKING_DIR
from helpers import apply_code_changes, get_code_ingest, log, get_updated_repo, CODE_FORMAT, push_code_changes

# TODO: Check how to address line reviews
def handle_pr_review(payload):
    review = payload["review"]
    pr = payload["pull_request"]
    repo_clone_url = payload["repository"]["clone_url"]
    branch_name = pr["head"]["ref"]
    review_comments = review["body"]

    log(f"Received review feedback for PR:\n\n {review['body']}")

    print(f"🚀 Addressing review feedback for branch: {branch_name}")

    # Go to the PR branch
    repo_path, repo = get_updated_repo(repo_clone_url)

    # Fetch the latest changes from the origin remote
    repo.remotes.origin.fetch()
    log("Fetched latest changes from origin.")

    # Checkout the specific PR branch
    repo.git.checkout(branch_name)

    # Hard reset the local branch to match the remote branch
    repo.git.reset('--hard', f'origin/{branch_name}')
    log(f"Checked out and reset branch '{branch_name}' to remote state.")
    
    # Get PR Diff for context
    diff_url = pr["diff_url"]
    diff_response = requests.get(diff_url)
    pr_diff = diff_response.text
    log("Fetched PR diff for context.")

    # Request Changes from Gemini
    prompt = f"""
    You are an expert software developer revising a pull request based on feedback.
    Analyze the review comments and the provided PR diff. Generate the necessary code changes to address the feedback.

    {CODE_FORMAT}

    ## REVIEW FEEDBACK:
    {review_comments}

    ## PR DIFF:
    ```diff
    {pr_diff}
    ```

    ## CODE:
    {get_code_ingest()}

    """
    
    log("Sending revision request to Gemini...")
    response = gemini_model.generate_content(prompt)
    
    apply_code_changes(repo_path, response.text)
    
    if not repo.is_dirty(untracked_files=True):
        log("No changes were applied from review feedback.")
        return

    repo.git.add(A=True)
    log("Changes applied from review feedback. Committing changes...")

    diff = repo.git.diff('HEAD')
    commit_message_prompt = f"""
        Based on the following code changes (diff) provide **only** a concise and informative **git commit message** that summarizes the changes.

        **Code Diff:**
        ```diff
        {diff}
        ```
    """

    if flash_model:
        commit_message = flash_model.generate_content(commit_message_prompt).text.strip()
    else:
        commit_message = "Address PR review feedback"


    repo.index.commit(commit_message)

    push_code_changes(repo, branch_name, repo_clone_url)

    print(f"✅ Successfully reviewed code")
