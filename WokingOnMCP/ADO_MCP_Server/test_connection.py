"""
Simple test script to verify Azure DevOps credentials and connection
Run: python test_connection.py
"""
import os
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

# Get config
ADO_ORG_URL = os.getenv("AZURE_DEVOPS_ORG_URL")
ADO_PAT = os.getenv("AZURE_DEVOPS_PAT")
DEFAULT_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
API_VERSION = os.getenv("AZURE_DEVOPS_API_VERSION", "7.0")

print("=" * 60)
print("🔍 Azure DevOps Connection Test")
print("=" * 60)

# Check if variables are loaded
print("\n1️⃣ Checking environment variables...")
print(f"   ORG_URL: {'✅ Set' if ADO_ORG_URL else '❌ Missing'}")
print(f"   PAT: {'✅ Set' if ADO_PAT else '❌ Missing'}")
print(f"   PROJECT: {'✅ Set' if DEFAULT_PROJECT else '❌ Missing'}")

if ADO_ORG_URL:
    print(f"   URL Value: {ADO_ORG_URL}")
if ADO_PAT:
    print(f"   PAT Length: {len(ADO_PAT)} characters")
    print(f"   PAT Preview: {ADO_PAT[:10]}...{ADO_PAT[-10:]}")
if DEFAULT_PROJECT:
    print(f"   Project: {DEFAULT_PROJECT}")

if not ADO_ORG_URL or not ADO_PAT:
    print("\n❌ Missing required environment variables!")
    print("   Please check your .env file")
    exit(1)

# Test 1: List projects (basic auth test)
print("\n2️⃣ Testing authentication with Projects API...")
url = f"{ADO_ORG_URL}/_apis/projects?api-version={API_VERSION}"
print(f"   URL: {url}")

try:
    response = requests.get(
        url,
        auth=HTTPBasicAuth("", ADO_PAT),
        timeout=15
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Authentication successful!")
        data = response.json()
        project_count = data.get("count", 0)
        print(f"   Found {project_count} project(s)")
        
        if project_count > 0:
            print("\n   Available projects:")
            for proj in data.get("value", [])[:10]:
                print(f"      - {proj.get('name')}")
    elif response.status_code == 401:
        print("   ❌ Authentication failed (401 Unauthorized)")
        print("   Possible reasons:")
        print("      - PAT is expired or invalid")
        print("      - PAT doesn't have 'Read' permissions")
        print("      - Organization URL is incorrect")
        print(f"\n   Response: {response.text[:200]}")
    elif response.status_code == 404:
        print("   ❌ Not Found (404)")
        print("   Organization URL might be incorrect")
        print(f"   Response: {response.text[:200]}")
    else:
        print(f"   ❌ Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 2: Check specific project access
if DEFAULT_PROJECT and response.status_code == 200:
    print(f"\n3️⃣ Testing access to project '{DEFAULT_PROJECT}'...")
    from urllib.parse import quote
    encoded_project = quote(DEFAULT_PROJECT, safe='')
    project_url = f"{ADO_ORG_URL}/_apis/projects/{encoded_project}?api-version={API_VERSION}"
    print(f"   URL: {project_url}")
    
    try:
        proj_response = requests.get(
            project_url,
            auth=HTTPBasicAuth("", ADO_PAT),
            timeout=15
        )
        
        print(f"   Status Code: {proj_response.status_code}")
        
        if proj_response.status_code == 200:
            print("   ✅ Project found and accessible!")
            proj_data = proj_response.json()
            print(f"   Project ID: {proj_data.get('id')}")
            print(f"   Project State: {proj_data.get('state')}")
        elif proj_response.status_code == 404:
            print("   ❌ Project not found")
            print(f"   Make sure '{DEFAULT_PROJECT}' exists in your organization")
        else:
            print(f"   ❌ Status: {proj_response.status_code}")
            print(f"   Response: {proj_response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

# Test 3: Check PAT permissions
if response.status_code == 200:
    print("\n4️⃣ Checking PAT permissions for work items...")
    # Try to query work items (read permission)
    wiql_url = f"{ADO_ORG_URL}/{quote(DEFAULT_PROJECT, safe='')}/_apis/wit/wiql?api-version={API_VERSION}"
    wiql_query = {
        "query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project ORDER BY [System.Id] DESC"
    }
    
    try:
        wiql_response = requests.post(
            wiql_url,
            json=wiql_query,
            auth=HTTPBasicAuth("", ADO_PAT),
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        print(f"   Status Code: {wiql_response.status_code}")
        
        if wiql_response.status_code == 200:
            print("   ✅ PAT has 'Read' permission for work items")
            wiql_data = wiql_response.json()
            item_count = len(wiql_data.get("workItems", []))
            print(f"   Found {item_count} work item(s) in project")
        elif wiql_response.status_code == 401:
            print("   ❌ PAT doesn't have work items permissions")
            print("   Required scopes: Work Items (Read, write, & manage)")
        else:
            print(f"   ⚠️  Status: {wiql_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("🏁 Test Complete")
print("=" * 60)

if response.status_code == 200:
    print("✅ Your ADO credentials are working!")
    print("\nNext steps:")
    print("   1. Make sure PAT has 'Work Items (Read, write, & manage)' scope")
    print("   2. Verify PAT hasn't expired at:")
    print("      https://dev.azure.com/neudesic-avis/_usersSettings/tokens")
    print("   3. Try creating a work item with the MCP server")
else:
    print("❌ There are authentication issues to resolve")
    print("\nTroubleshooting:")
    print("   1. Generate a new PAT at:")
    print("      https://dev.azure.com/neudesic-avis/_usersSettings/tokens")
    print("   2. Required scopes: Work Items (Read, write, & manage)")
    print("   3. Update .env file with the new PAT (no spaces around =)")
    print("   4. Run this test again")
