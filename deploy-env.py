#!/usr/bin/env python3
"""
Deploy environment variables from .env to Heroku.
Usage: python deploy-env.py
"""

import subprocess
import sys
from pathlib import Path

def load_env_file(env_path):
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        print(f"❌ Error: {env_path} not found")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def deploy_to_heroku(env_vars):
    """Deploy variables to Heroku."""
    if not env_vars:
        print("⚠️  No environment variables found")
        return
    
    # Check if Heroku CLI is installed
    try:
        subprocess.run(["heroku", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Heroku CLI not installed or not in PATH")
        print("Install it: https://devcenter.heroku.com/articles/heroku-cli")
        sys.exit(1)
    
    # Build the heroku config:set command
    config_args = [f"{k}={v}" for k, v in env_vars.items()]
    cmd = ["heroku", "config:set"] + config_args
    
    print(f"📤 Deploying {len(env_vars)} environment variables to Heroku...")
    print(f"Variables: {', '.join(env_vars.keys())}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Success!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error deploying to Heroku:")
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    env_path = Path("apps/backend/.env")
    env_vars = load_env_file(env_path)
    deploy_to_heroku(env_vars)
