import os
import re
import subprocess
import git

from configs import model, WORKING_DIR, DIGEST_DIR, GITHUB_TOKEN

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


def log(mylog):
    print("    - " + mylog)