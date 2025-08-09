import os
import re
import subprocess
import git
import requests
import octokit

from configs import WORKING_DIR, DIGEST_DIR, GITHUB_TOKEN

CODE_FORMAT = """
IMPORTANT: Provide the full, updated content for each file that needs to be changed. Your response MUST strictly follow this format, including the start and end markers:
--- START OF FILE: lib/path/to/your/file.dart ---
<<updated content of file.dart>>
--- END OF FILE: lib/path/to/your/file.dart ---
"""

def apply_code_changes(repo_path, gemini_response):
    print("🤖 Applying code changes from Gemini...")
    file_changes = re.findall(r"--- START OF FILE: (.*?) ---\n(.*?)\n--- END OF FILE: \1 ---", gemini_response, re.DOTALL)

    if not file_changes:
        print("⚠️ No file changes found in the Gemini response.")
        return

    changed_files = []
    for file_path, content in file_changes:
        full_path = os.path.join(repo_path, file_path.strip())
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        content_to_write = content.strip()
        
        match = re.match(r"```(?:\w+)?\n(.*?)\n```$", content_to_write, re.DOTALL)
        if match:
            content_to_write = match.group(1)

        # Write the new content to the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content_to_write)
        
        log(f"Updated {file_path}")
        changed_files.append(full_path)

    format_changed_files(repo_path, changed_files)

def format_changed_files(repo_path, files):

    if not files:
        return

    log("Formatting changed files...")
    
    files_by_ext = {}
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext not in files_by_ext:
            files_by_ext[ext] = []
        files_by_ext[ext].append(f)

    # Dart Files
    if '.dart' in files_by_ext:
        dart_files = files_by_ext['.dart']
        command = ["dart", "format"] + dart_files
        result = subprocess.run(
            command,
            cwd=repo_path, 
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        # TODO: better logging
        if result.stdout:
            print(result.stdout.strip())
    
    # TODO: Add support for other file types and their respective formatters

def get_code_ingest():
    log("Running 'gitingest' to create code digest...")
    subprocess.run(
        ["gitingest"], 
        cwd=DIGEST_DIR, 
        check=True, # Raise an exception for non-zero exit codes.
        capture_output=True, # Capture stdout/stderr to prevent printing unless needed.
        text=True
    )

    digest_path = os.path.join(DIGEST_DIR, 'digest.txt')
    if not os.path.exists(digest_path):
        print("⚠️ 'digest.txt' not found. Cannot proceed with code context.")
        raise FileNotFoundError("The digest.txt file was not created by gitingest.")
    
    log("Ingested code from the '/lib' directory.")

    with open(digest_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_updated_repo(repo_clone_url):
    repo_path = os.path.join(WORKING_DIR)
    if os.path.exists(repo_path):
        repo = git.Repo(repo_path)
        repo.git.checkout('main')
        repo.remotes.origin.pull()
    else:
        repo = git.Repo.clone_from(repo_clone_url, repo_path)
    
    log("Pulled latest changes from 'main' branch.")
    return repo_path, repo

def push_code_changes(repo, branch_name, repo_clone_url):
    push_url = repo_clone_url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
    origin = repo.remote(name='origin')
    origin.set_url(push_url)
    origin.push(refspec=f'{branch_name}:{branch_name}', force=True)
    log(f"Committed and pushed changes to branch '{branch_name}'.")

def get_issue_attachments(issue_number, repo_full_name):
    log(f"Fetching attachments for issue #{issue_number} in {repo_full_name}...")
    owner, repo_name = repo_full_name.split('/')
    url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.full+json",
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        html_body = data.get("body_html")
        if not html_body:
            return []
            
        image_urls = re.findall(r'<img src="([^"]+)"', html_body)
        if not image_urls:
            return []
                  
        attachments = []
        for url in image_urls:
            content_type, image_data = fetch_image_from_url(url, GITHUB_TOKEN)
            if content_type and image_data:
                attachments.append({'mime_type': content_type, 'data': image_data})
        return attachments
    else:
        log(f"Failed to fetch issue attachments: {response.status_code}")
        return []


def fetch_image_from_url(url, token):

    """Fetches an image from a URL using a GitHub token and returns its mime type and data."""
    try:
        headers = {'Authorization': f'token {token}'}
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type')
        if not content_type or 'application/octet-stream' in content_type:
            guessed_type = guess_type(url)[0]
            if guessed_type:
                content_type = guessed_type
        
        if not content_type or not content_type.startswith('image/'):
            log(f"Skipping non-image URL: {url} (Content-Type: {content_type})")
            return None, None

        image_data = response.content
        log(f"Successfully fetched image from {url}")
        return content_type, image_data
    except requests.exceptions.RequestException as e:
        log(f"Warning: Could not fetch image from {url}. Error: {e}")
        return None, None

def get_pr_template(repo_path):
    """
    Checks for a pull request template file and returns its content.
    Searches in standard GitHub locations: root, .github/, and docs/.
    """
    log("Checking for a PR template...")
    # Standard locations and names for PR templates
    possible_paths = [
        os.path.join(repo_path, 'pull_request_template.md'),
        os.path.join(repo_path, '.github', 'pull_request_template.md'),
        os.path.join(repo_path, 'docs', 'pull_request_template.md'),
        os.path.join(repo_path, 'PULL_REQUEST_TEMPLATE.md'),
        os.path.join(repo_path, '.github', 'PULL_REQUEST_TEMPLATE.md'),
        os.path.join(repo_path, 'docs', 'PULL_REQUEST_TEMPLATE.md')
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                log(f"Found PR template at: {os.path.relpath(path, repo_path)}")
                return content

    log("No PR template found.")
    return None

def log(mylog):
    print("    - " + mylog)