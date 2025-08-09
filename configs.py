from nis import cat
from dotenv.main import load_dotenv
import os
import re
import git
import requests
import google.generativeai as genai
from github import Github
import subprocess

# Env variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MY_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode('utf-8')

WORKING_DIR = "../project_luca/app"
DIGEST_DIR = os.path.join(WORKING_DIR, 'lib')
RULES_FILE = os.path.join(WORKING_DIR, 'rules.txt')

g = Github(GITHUB_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-pro')
flash_model = genai.GenerativeModel('gemini-2.5-flash')
gemma_model = genai.GenerativeModel('gemma-3n-e2b-it')
