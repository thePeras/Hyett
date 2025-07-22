import os
import re
import subprocess

from configs import model, WORKING_DIR, DIGEST_DIR

def apply_code_changes(repo_path, gemini_response):
    print("🤖 Applying code changes from Gemini...")
    file_changes = re.findall(r"--- START OF FILE: (.*?) ---\n(.*?)\n--- END OF FILE: \1 ---", gemini_response, re.DOTALL)

    if not file_changes:
        print("⚠️ No file changes found in the Gemini response.")
        return

    for file_path, content in file_changes:
        full_path = os.path.join(repo_path, file_path.strip())
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        content_to_write = content.strip()
        
        # If the AI includes markdown fences like ```dart, strip them.
        match = re.match(r"```(?:\w+)?\n(.*?)\n```$", content_to_write, re.DOTALL)
        if match:
            content_to_write = match.group(1)

        with open(full_path, 'w') as f:
            f.write(content_to_write)
        print(f"   - Updated {full_path}")
    
    #TODO: Format changed files

def get_code_ingest():
    log("   - Running 'gitingest' to create code digest...")
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
    
    log("   - Ingested code from the '/lib' directory.")

    with open(digest_path, 'r', encoding='utf-8') as f:
        return f.read()

def log(mylog):
    print("    - " + mylog)