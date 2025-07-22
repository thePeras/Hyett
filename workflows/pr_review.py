import os
import requests
import git

from configs import model, WORKING_DIR, GITHUB_TOKEN
from helpers import apply_code_changes, get_code_ingest, log

def handle_pr_review(payload):
    review = payload["review"]
    pr = payload["pull_request"]

    repo_clone_url = payload["repository"]["clone_url"]
    branch_name = pr["head"]["ref"]
    review_comments = review["body"]

    log(f"Received review feedback for PR: {review['body']}")

    print(f"🚀 Addressing review feedback for branch: {branch_name}")

    # Go to the PR branch
    repo_path = os.path.join(WORKING_DIR)
    repo = git.Repo(repo_path)
    origin = repo.remote(name='origin')
    origin.pull()
    repo.git.checkout(branch_name)
    log(f"Checked out branch '{branch_name}'.")
    
    # Get PR Diff for context
    # We use requests here as PyGithub's diff handling can be tricky
    diff_url = pr["diff_url"]
    diff_response = requests.get(diff_url)
    pr_diff = diff_response.text
    log("Fetched PR diff for context.")

    # Request Changes from Gemini
    prompt = f"""
    You are an expert software developer revising a pull request based on feedback.
    Analyze the review comments and the provided PR diff. Generate the necessary code changes to address the feedback.

    IMPORTANT: Provide the full, updated content for each file that needs to be changed, using the same strict format as before:
    --- START OF FILE: lib/path/to/your/file.dart ---
    <<updated content of file.dart>>
    --- END OF FILE: lib/path/to/your/file.dart ---

    ## REVIEW FEEDBACK:
    {review_comments}

    ## PR DIFF:
    ```diff
    {pr_diff}
    ```

    ## CODE FROM '/lib' FOLDER:
    {get_code_ingest()}

    """
    
    log("Sending revision request to Gemini...")
    response = model.generate_content(prompt)
    
    apply_code_changes(repo_path, response.text)
    
    if not repo.is_dirty(untracked_files=True):
        log("No changes were applied from review feedback.")
        return

    repo.git.add(A=True)
    repo.index.commit("refactor: Address PR review feedback")
    
    push_url = repo_clone_url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
    origin.set_url(push_url)
    origin.push()
    
    print(f"✅ Successfully pushed updates to branch '{branch_name}'.")
