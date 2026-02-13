#!/usr/bin/env python3
"""
Decode JWT token from login to check for tenant_id
"""
import base64
import json
import re

# Extract the JWT token from the WebSocket error message
jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJCOUxXclRobl9oa2Z6bFo0YlYzTTZrSXhrWDlVUGh3SC1BNW5vU0U2Sk53In0.eyJleHAiOjE3NzA3MDQyMjgsImlhdCI6MTc3MDcwMzMyOCwiYXV0aF90aW1lIjoxNzcwNzAzMzI4LCJqdGkiOiIwNmQzNzAxNi0xZjI5LTRiYzYtOTZjYy1kODc2OTgzZWQ4YzUiLCJpc3MiOiJodHRwczovLzE5Mi4xNjguMTAuNTMvcmVhbG1zL3B1bHNlIiwiYXVkIjpbInB1bHNlLXVpIiwiYWNjb3VudCJdLCJzdWIiOiJlZDNmOTg2OC0xMjczLTQ1ZTMtYmEzYS0wNDc4OTU3MzQxODgiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJwdWxzZS11aSIsIm5vbmNlIjoiZjRlN2Y5ZDUtZmNjMC00MWE4LTlmNDktOTQxODQ0OWJlMWI1Iiwic2Vzc2lvbl9zdGF0ZSI6IjRiMzI1YWVlLTIxMjctNGIyYi04OWRlLTM2NjZkMGM2OTc4NyIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cHM6Ly8xOTIuMTY4LjEwLjUzIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLXB1bHNlIiwib2ZmbGluZV9hY2Nlc3MiLCJjdXN0b21lciIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsInNpZCI6IjRiMzI1YWVlLTIxMjctNGIyYi04OWRlLTM2NjZkMGM2OTc4NyIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkFjbWUgQWRtaW4iLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhY21lLWFkbWluIiwiZ2l2ZW5fbmFtZSI6IkFjbWUiLCJmYW1pbHlfbmFtZSI6IkFkbWluIiwiZW1haWwiOiJhZG1pbkBhY21lLWluZHVzdHJpYWwuY29tIn0.tmfWhsyUlsM6eRsd0JBQX8K6c3ZFyk5LVKkMqSOrHz7aEPBSN8oE1llKJL81EhLEKkgaXkeNTk7udz9je1vBF2UoIlkGaxEDaQikBN89bBJ8yHBjuJdv248Wp7E_V2ntyN1eS1l774qWFmjaOyHqfokWSyCoq8J5wFCUchNIdRE_sQMP2LMTFw69-aUAdzqIvyoLkVFXYHQsGrROPZlyOrFlaVbkzhJplQLbLSyjJ2U9Brd8XmwBHOnOAE06pfeuYdu1K0-o6veeReqYCSf3UREFFGgYeWCz40F9cIqogo0kiIDpNr32Ov9N4GWGJ6UctyifT1czL9wT2O7Zy5H9cw"

def decode_jwt(token):
    """Decode JWT token (header and payload only, no verification)"""
    parts = token.split('.')
    if len(parts) != 3:
        print(f"Invalid JWT format: expected 3 parts, got {len(parts)}")
        return None, None
    
    header_encoded, payload_encoded, signature = parts
    
    # Decode header
    try:
        # Add padding if needed
        header_padded = header_encoded + '=' * (4 - len(header_encoded) % 4)
        header_json = base64.urlsafe_b64decode(header_padded)
        header = json.loads(header_json)
    except Exception as e:
        print(f"Error decoding header: {e}")
        header = None
    
    # Decode payload
    try:
        # Add padding if needed
        payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
        payload_json = base64.urlsafe_b64decode(payload_padded)
        payload = json.loads(payload_json)
    except Exception as e:
        print(f"Error decoding payload: {e}")
        payload = None
    
    return header, payload

print("="*80)
print("JWT TOKEN ANALYSIS")
print("="*80)

header, payload = decode_jwt(jwt_token)

if header:
    print("\nHEADER:")
    print(json.dumps(header, indent=2))

if payload:
    print("\nPAYLOAD:")
    print(json.dumps(payload, indent=2))
    
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    
    # Check for tenant_id
    if 'tenant_id' in payload:
        print(f"✓ tenant_id FOUND: {payload['tenant_id']}")
    else:
        print("✗ tenant_id NOT FOUND in token payload")
    
    # Show key fields
    print(f"\nUser Information:")
    print(f"  - sub (user ID): {payload.get('sub', 'N/A')}")
    print(f"  - preferred_username: {payload.get('preferred_username', 'N/A')}")
    print(f"  - email: {payload.get('email', 'N/A')}")
    print(f"  - name: {payload.get('name', 'N/A')}")
    
    print(f"\nRoles:")
    realm_access = payload.get('realm_access', {})
    roles = realm_access.get('roles', [])
    for role in roles:
        print(f"  - {role}")
    
    print(f"\nIssuer: {payload.get('iss', 'N/A')}")
    print(f"Token Type: {payload.get('typ', 'N/A')}")
    print(f"Client ID (azp): {payload.get('azp', 'N/A')}")
    
    # Check all keys for any tenant-related fields
    print(f"\nAll Token Claims:")
    for key in sorted(payload.keys()):
        if 'tenant' in key.lower():
            print(f"  - {key}: {payload[key]} ← TENANT-RELATED")
        else:
            print(f"  - {key}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)
print("The JWT token from Keycloak does NOT contain a 'tenant_id' claim.")
print("This is likely why all API calls are returning 403 Forbidden.")
print("The backend API expects tenant_id in the token but Keycloak is not")
print("providing it during authentication.")
print("="*80)
