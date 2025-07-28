from helpers import log
import os
import re
import json

from configs import WORKING_DIR, GITHUB_TOKEN, model, g
from helpers import apply_code_changes, get_code_ingest, get_updated_repo, CODE_FORMAT, push_code_changes, fetch_image_from_url, get_issue_attachments, get_pr_template

# --- Workflow 1: Handle New Issue Assignment ---
def handle_issue_assigned(payload):
    try:
        repo_full_name = payload["repository"]["full_name"]
        repo_clone_url = payload["repository"]["clone_url"]
        issue_number = payload["issue"]["number"]
        issue_title = payload["issue"]["title"]
        issue_body = payload["issue"]["body"]

        print(f"🚀 Starting work on issue #{issue_number}: {issue_title}")

        repo_path, repo = get_updated_repo(repo_clone_url)
        code_context = get_code_ingest()
        pr_template = get_pr_template(repo_path)

        # Request Code Changes from Gemini
        code_gen_prompt = f"""
        You are an expert software developer tasked with fixing a GitHub issue.
        Analyze the issue description and the provided code from the project's 'lib' folder.
        Generate the necessary code changes to resolve the issue.

        {CODE_FORMAT}

        ## GITHUB ISSUE:
        - **Title:** {issue_title}
        - **Description:** {issue_body}

        ## CODE:
        {code_context}
        """
        
        attachments = get_issue_attachments(issue_number, repo_full_name)
        if attachments:
            log(f"Found {len(attachments)} image attachment(s).")

        log("Sending request to Gemini for code generation...")
        gemini_request_contents = [code_gen_prompt] + attachments
        response = model.generate_content(gemini_request_contents)

        log("Received response from Gemini. Applying changes to main branch locally...")
        apply_code_changes(repo_path, response.text)
        
        if not repo.is_dirty(untracked_files=True):
            log("No changes were applied. Aborting PR creation.")
            return

        diff = repo.git.diff('HEAD')

        if pr_template:
            pr_description_instruction = f"""
        4. A detailed Pull Request description. IMPORTANT: You must use the following template to structure your description, filling in the relevant sections based on the code changes.

        **PR Template:**
        ```markdown
        {pr_template}
        ```
        """
        else:
            pr_description_instruction = "4. A short, well-written Pull Request description."

        # Ask PR details based on the diff
        pr_details_prompt = f"""
        Based on the following code changes (diff) and the original issue title, please provide:
        1. A descriptive git branch name.
        2. A concise Pull Request title.
        3. A commit message that summarizes the changes.
        {pr_description_instruction}

        **GitHub Issue Title:** {issue_title}

        **Code Diff:**
        ```diff
        {diff}
        ```

        **Response Format:**
        Your response must be a single JSON object with the keys "branch_name", "pr_title", "commit_message", and "pr_description". Do not add any other text or markdown formatting.
        Example:
        {{
          "branch_name": "feat/add-user-authentication",
          "pr_title": "Feat: Implement user authentication",
          "commit_message": "Implement user authentication",
          "pr_description": "This PR introduces user authentication, addressing issue #{issue_number}. It adds the necessary models, routes, and services for user sign-up and login."
        }}
        """
        log("Sending request to Gemini for branch name, PR title, and description...")
        details_response = model.generate_content(pr_details_prompt)

        try:
            json_match = re.search(r"\{.*\}", details_response.text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in Gemini's response for PR details.")
            pr_details = json.loads(json_match.group(0))
            branch_name = pr_details["branch_name"]
            pr_title = pr_details["pr_title"]
            pr_description = pr_details["pr_description"]
            commit_message = pr_details.get("commit_message", pr_title)
            log(f"Received PR details from Gemini. Branch: {branch_name}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log(f"Error parsing Gemini's response for PR details: {e}. Using defaults.")
            branch_name = f"fix/issue-{issue_number}"
            pr_title = f"Fix: {issue_title}"
            commit_message = f"Fix issue #{issue_number}: {issue_title}"
            pr_description = f"Closes #{issue_number}"

        pr_description = f"Closes #{issue_number}\n\n{pr_description}"
        # TODO: use a image badge
        pr_description = f"{pr_description}\n\n*Created by [Hyett](https://github.com/theperas/hyett).*"

        if branch_name in repo.heads:
            repo.delete_head(branch_name, '-D')
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        log(f"Created and checked out new branch: {branch_name}")

        repo.git.add(A=True)
        repo.index.commit(commit_message)

        push_code_changes(repo, branch_name, repo_clone_url)
    
        # TODO: Why not using repo var?
        gh_repo = g.get_repo(repo_full_name)
        pr = gh_repo.create_pull(
            title=pr_title,
            body=pr_description,
            head=branch_name,
            base="main"
        )
        print(f"✅ Successfully created PR: {pr.html_url}")
    except Exception as e:
        print(f"❌ Error handling issue assignment: {e}")
        return