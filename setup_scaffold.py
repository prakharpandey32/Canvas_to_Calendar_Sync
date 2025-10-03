"""
Setup files for Canvas-Outlook MCP Server
Save these as separate files in your project directory
"""

# ============================================================================
# FILE 1: requirements.txt
# ============================================================================
REQUIREMENTS = """mcp
requests
msal
python-dateutil
"""

# ============================================================================
# FILE 2: .env.example (Copy to .env and fill in your values)
# ============================================================================
ENV_EXAMPLE = """# Canvas API Token
# Get from: https://canvas.harvard.edu/profile/settings
CANVAS_API_TOKEN=your_canvas_token_here

# Microsoft Graph API (Outlook) Credentials
# Get from: https://portal.azure.com
OUTLOOK_CLIENT_ID=your_client_id_here
OUTLOOK_CLIENT_SECRET=your_client_secret_here
OUTLOOK_TENANT_ID=common
"""

# ============================================================================
# FILE 3: config_helper.py (Helper to set up environment)
# ============================================================================
CONFIG_HELPER = """#!/usr/bin/env python3
'''
Configuration Helper for Canvas-Outlook MCP Server
Run this to set up your environment variables
'''

import os
from pathlib import Path

def setup_config():
    print("🔧 Canvas-Outlook MCP Server Configuration\\n")
    
    # Get Canvas token
    print("Step 1: Canvas API Token")
    print("  1. Go to: https://canvas.harvard.edu/profile/settings")
    print("  2. Scroll to 'Approved Integrations'")
    print("  3. Click '+ New Access Token'")
    print("  4. Give it a name and generate\\n")
    
    canvas_token = input("Enter your Canvas API token: ").strip()
    
    # Get Outlook credentials
    print("\\nStep 2: Microsoft Outlook/Graph API (Optional for now)")
    print("  1. Go to: https://portal.azure.com")
    print("  2. Register a new application")
    print("  3. Add Calendars.ReadWrite permission")
    print("  4. Create a client secret\\n")
    
    use_outlook = input("Set up Outlook now? (y/n): ").lower() == 'y'
    
    outlook_client_id = ""
    outlook_secret = ""
    
    if use_outlook:
        outlook_client_id = input("Enter Outlook Client ID: ").strip()
        outlook_secret = input("Enter Outlook Client Secret: ").strip()
    
    # Write to .env file
    env_content = f'''# Canvas API Token
CANVAS_API_TOKEN={canvas_token}

# Microsoft Graph API (Outlook) Credentials
OUTLOOK_CLIENT_ID={outlook_client_id}
OUTLOOK_CLIENT_SECRET={outlook_secret}
OUTLOOK_TENANT_ID=common
'''
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\\n✅ Configuration saved to .env file!")
    print("\\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Test the server: python server.py")

if __name__ == "__main__":
    setup_config()
"""

# ============================================================================
# FILE 4: test_server.py (Test your setup)
# ============================================================================
TEST_SERVER = """#!/usr/bin/env python3
'''
Test script for Canvas-Outlook MCP Server
'''

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CANVAS_TOKEN = os.getenv("CANVAS_API_TOKEN")
CANVAS_BASE_URL = "https://canvas.harvard.edu/api/v1"

def test_canvas_connection():
    '''Test Canvas API connection'''
    print("🧪 Testing Canvas API connection...\\n")
    
    if not CANVAS_TOKEN:
        print("❌ CANVAS_API_TOKEN not set!")
        print("Run: python config_helper.py")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}
        response = requests.get(f"{CANVAS_BASE_URL}/users/self", headers=headers)
        response.raise_for_status()
        
        user = response.json()
        print(f"✅ Connected to Canvas!")
        print(f"   User: {user.get('name', 'Unknown')}")
        print(f"   Email: {user.get('primary_email', 'Unknown')}\\n")
        
        # Test courses
        response = requests.get(
            f"{CANVAS_BASE_URL}/courses?enrollment_state=active",
            headers=headers
        )
        courses = response.json()
        
        print(f"✅ Found {len(courses)} active courses:")
        for course in courses[:5]:  # Show first 5
            print(f"   - {course.get('name', 'Unknown')}")
        
        if len(courses) > 5:
            print(f"   ... and {len(courses) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_outlook_connection():
    '''Test Outlook API connection'''
    print("\\n🧪 Testing Outlook API connection...\\n")
    
    client_id = os.getenv("OUTLOOK_CLIENT_ID")
    client_secret = os.getenv("OUTLOOK_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("⚠️  Outlook credentials not set (optional)")
        print("   You can set these up later for calendar sync")
        return True
    
    try:
        from msal import ConfidentialClientApplication
        
        app = ConfidentialClientApplication(
            client_id,
            authority="https://login.microsoftonline.com/common",
            client_credential=client_secret,
        )
        
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" in result:
            print("✅ Outlook authentication successful!")
            return True
        else:
            print(f"❌ Outlook auth failed: {result.get('error_description')}")
            return False
            
    except ImportError:
        print("⚠️  msal not installed (needed for Outlook)")
        print("   Run: pip install msal")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Canvas-Outlook MCP Server Test Suite")
    print("=" * 60 + "\\n")
    
    canvas_ok = test_canvas_connection()
    outlook_ok = test_outlook_connection()
    
    print("\\n" + "=" * 60)
    if canvas_ok:
        print("✅ Your MCP server is ready to use!")
        print("\\nRun: python server.py")
    else:
        print("❌ Please fix the errors above before running the server")
    print("=" * 60)
"""

# ============================================================================
# FILE 5: README.md
# ============================================================================
README = """# Canvas-Outlook Calendar Sync MCP Server

Automatically sync your Canvas assignments and exams to your Outlook calendar.

## Features

- ✅ Fetch all active courses from Canvas
- ✅ Extract assignment due dates
- ✅ Find exam dates from calendar events
- ✅ Sync to Outlook/Microsoft 365 calendar
- ✅ Bypasses Duo (uses API tokens)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Canvas API Token

1. Go to https://canvas.harvard.edu/profile/settings
2. Scroll to "Approved Integrations"
3. Click "+ New Access Token"
4. Give it a purpose: "MCP Calendar Sync"
5. Copy the token

### 3. Configure

Run the configuration helper:

```bash
python config_helper.py
```

Or manually create a `.env` file:

```env
CANVAS_API_TOKEN=your_token_here
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_secret
```

### 4. Test

```bash
python test_server.py
```

### 5. Run

```bash
python server.py
```

## Usage in Claude Desktop

Add to your Claude config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "canvas-outlook": {
      "command": "python",
      "args": ["/path/to/your/server.py"],
      "env": {
        "CANVAS_API_TOKEN": "your_token",
        "OUTLOOK_CLIENT_ID": "your_client_id",
        "OUTLOOK_CLIENT_SECRET": "your_secret"
      }
    }
  }
}
```

## Available Tools

### `check_configuration`
Verify your API tokens are set correctly

### `fetch_courses`
Get list of all active Canvas courses

### `fetch_course_assignments`
Get assignments for a specific course

### `fetch_all_assignments`
Get all assignments and events from all courses

### `sync_to_outlook`
Sync fetched items to your Outlook calendar

## Example Workflow

In Claude Desktop:

```
You: Check my Canvas configuration
Claude: [calls check_configuration tool]

You: Fetch all my courses
Claude: [calls fetch_courses tool]

You: Get all assignments from all my courses
Claude: [calls fetch_all_assignments tool]

You: Sync everything to my Outlook calendar
Claude: [calls sync_to_outlook tool]
```

## Troubleshooting

### Canvas API Issues

- Make sure token is valid (they can expire)
- Check you have access to courses
- Verify Canvas URL is correct

### Outlook Issues

- Ensure app is registered in Azure Portal
- Check API permissions include Calendars.ReadWrite
- Verify client secret hasn't expired

## Security Notes

- Never commit `.env` file to version control
- Keep API tokens secure
- Canvas tokens have full access to your account
- Consider token expiration dates

## Next Steps

- Add filtering for specific assignment types
- Support for multiple calendars
- Automatic daily sync
- Email notifications for upcoming deadlines
"""

# ============================================================================
# Save all files
# ============================================================================

if __name__ == "__main__":
    import os
    
    files = {
        "requirements.txt": REQUIREMENTS,
        ".env.example": ENV_EXAMPLE,
        "config_helper.py": CONFIG_HELPER,
        "test_server.py": TEST_SERVER,
        "README.md": README
    }
    
    print("Creating setup files...\\n")
    
    for filename, content in files.items():
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✅ Created: {filename}")
    
    print("\\n✅ All setup files created!")
    print("\\nNext steps:")
    print("  1. Run: python config_helper.py")
    print("  2. Run: python test_server.py")
    print("  3. Run: python server.py")
