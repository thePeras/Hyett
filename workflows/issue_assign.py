from helpers import log
import os
import git
import requests

from configs import WORKING_DIR, GITHUB_TOKEN, model, g
from helpers import apply_code_changes, get_code_ingest

# --- Workflow 1: Handle New Issue Assignment ---
def handle_issue_assigned(payload):
    try:
        repo_full_name = payload["repository"]["full_name"]
        repo_clone_url = payload["repository"]["clone_url"]
        issue_number = payload["issue"]["number"]
        issue_title = payload["issue"]["title"]
        issue_body = payload["issue"]["body"]

        print(f"🚀 Starting work on issue #{issue_number}: {issue_title}")

        # Clone Repo and Create Branch
        repo_path = os.path.join(WORKING_DIR)
        if os.path.exists(repo_path):
            repo = git.Repo(repo_path)
            repo.git.checkout('main')
            repo.remotes.origin.pull()
        else:
            repo = git.Repo.clone_from(repo_clone_url, repo_path)
        
        # TODO: better branch name
        branch_name = f"fix/issue-{issue_number}"
        if branch_name in repo.heads:
            repo.delete_head(branch_name, '-D') # Delete old branch if it exists
        new_branch = repo.create_head(branch_name, 'origin/main') # Base off main
        new_branch.checkout()
        log(f"Cloned repo and created new branch: {branch_name}")

        # Ingest code from the '/lib' folder
        lib_path = os.path.join(repo_path, 'lib')

        code_context = get_code_ingest()

        # Request Changes from Gemini
        prompt = f"""
        You are an expert software developer tasked with fixing a GitHub issue.
        Analyze the issue description and the provided code from the project's 'lib' folder.
        Generate the necessary code changes to resolve the issue.

        IMPORTANT: Provide the full, updated content for each file that needs to be changed. Your response MUST strictly follow this format, including the start and end markers:
        --- START OF FILE: lib/path/to/your/file.dart ---
        <<updated content of file.dart>>
        --- END OF FILE: lib/path/to/your/file.dart ---

        ## GITHUB ISSUE:
        - **Title:** {issue_title}
        - **Description:** {issue_body}

        ## CODE FROM '/lib' FOLDER:
        {code_context}
        """
        
        log("Sending request to Gemini...")
        response = model.generate_content(prompt)
        
        log("Received response from Gemini. Applying changes...")
        apply_code_changes(repo_path, response.text)
        
        if not repo.is_dirty(untracked_files=True):
            log("No changes were applied. Aborting PR creation.")
            return

        repo.git.add(A=True)
        # TODO: better commit message
        repo.index.commit(f"feat: Fix for issue #{issue_number}")
        
        # Use token for push authentication
        push_url = repo_clone_url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
        origin = repo.remote(name='origin')
        origin.set_url(push_url)
        origin.push(refspec=f'{branch_name}:{branch_name}', force=True)
        print(f"   - Committed and pushed changes to branch '{branch_name}'.")

        gh_repo = g.get_repo(repo_full_name)
        # TODO: better PR description with diff changes
        pr_body = f"This PR is an AI-generated solution for issue #{issue_number}.\n\n**Issue:** {issue_title}\n\n*Please review the changes carefully before merging.*"
        pr = gh_repo.create_pull(
            title=f"Fix: {issue_title}",
            body=pr_body,
            head=branch_name,
            base="main"
        )
        print(f"✅ Successfully created PR: {pr.html_url}")
    except Exception as e:
        print(f"❌ Error handling issue assignment: {e}")
        return
