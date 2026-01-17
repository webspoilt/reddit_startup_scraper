#!/usr/bin/env python3
"""
Gemini API Key Diagnostic Tool
Run this script to test your Gemini API key and diagnose connection issues.
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_key_format():
    """Test if the API key has the correct format."""
    api_key = os.getenv("GEMINI_API_KEY", "")

    print("=" * 60)
    print("GEMINI API KEY DIAGNOSTIC TOOL")
    print("=" * 60)
    print()

    # Check if API key is set
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY is not set in .env file")
        print()
        print("To fix this:")
        print("1. Go to https://aistudio.google.com/app/apikey")
        print("2. Click 'Create API Key'")
        print("3. Copy the key and paste it in your .env file")
        print("   Format: GEMINI_API_KEY=your_key_here")
        return False

    print(f"✓ API Key found")
    print(f"  Length: {len(api_key)} characters")
    print(f"  First 10 chars: {api_key[:10]}...")

    # Validate API key format
    if not api_key.startswith("AIza"):
        print("❌ ERROR: API key doesn't start with 'AIza' (invalid format)")
        print()
        print("To fix this:")
        print("1. Go to https://aistudio.google.com/app/apikey")
        print("2. Create a new API key")
        print("3. Make sure to copy the ENTIRE key")
        return False

    if len(api_key) != 39:
        print(f"⚠️  WARNING: API key length is {len(api_key)}, expected 39 characters")
        print("   This might cause issues. Consider generating a new key.")

    print("✓ API key format looks correct")
    return True


def test_gemini_connection():
    """Test the actual Gemini API connection."""
    api_key = os.getenv("GEMINI_API_KEY", "")

    print()
    print("-" * 60)
    print("TESTING GEMINI API CONNECTION")
    print("-" * 60)
    print()

    # Try the stable google-generativeai package first
    try:
        import google.generativeai as genai
        print("✓ google-generativeai package is installed")

        # Configure the API
        genai.configure(api_key=api_key)
        print("✓ API key configured")

        # List available models
        print()
        print("Checking available models...")

        # Try models in order of preference
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]

        for model_name in models_to_try:
            try:
                print(f"  Testing {model_name}...", end=" ")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hi", generation_config={"max_output_tokens": 10})

                if response and hasattr(response, 'text') and response.text:
                    print("✓ SUCCESS")
                    print()
                    print(f"✓ Model {model_name} is working!")
                    print(f"  Response: {response.text.strip()}")
                    return True
                else:
                    print("Empty response")

            except Exception as e:
                error_msg = str(e).lower()
                if "404" in error_msg or "not found" in error_msg:
                    print("Model not available")
                elif "400" in error_msg or "bad request" in error_msg:
                    print("Invalid request - likely API key issue")
                    print(f"   Error: {e}")
                elif "429" in error_msg or "rate limit" in error_msg:
                    print("Rate limited - try again later")
                elif "api key" in error_msg or "unauthorized" in error_msg:
                    print("API key invalid or missing permissions")
                    print(f"   Error: {e}")
                else:
                    print(f"Error: {type(e).__name__}: {e}")
                continue

        print()
        print("❌ No working model found")
        return False

    except ImportError:
        print("❌ google-generativeai package not found")
        print()
        print("To fix this:")
        print("1. Run: pip install google-generativeai")
        print("2. Or: pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def show_fix_instructions():
    """Show instructions for fixing common issues."""
    print()
    print("=" * 60)
    print("COMMON ISSUES AND SOLUTIONS")
    print("=" * 60)
    print()
    print("1. API KEY INVALID OR EXPIRED")
    print("   - Go to https://aistudio.google.com/app/apikey")
    print("   - Create a new API key")
    print("   - Update the .env file")
    print()
    print("2. API KEY DOESN'T HAVE GEMINI API ACCESS")
    print("   - Make sure you created the key in Google AI Studio")
    print("   - Keys from Google Cloud Console need additional setup")
    print()
    print("3. GEMINI API NOT ENABLED")
    print("   - Visit https://console.cloud.google.com/apis/library")
    print("   - Search for 'Gemini API'")
    print("   - Enable it for your project")
    print()
    print("4. RATE LIMIT EXCEEDED")
    print("   - Wait a few minutes and try again")
    print("   - The free tier has limited requests per minute")
    print()
    print("5. PACKAGE NOT INSTALLED")
    print("   - Run: pip install google-generativeai")
    print()


if __name__ == "__main__":
    print()

    # Test API key format
    key_ok = test_api_key_format()

    if key_ok:
        # Test actual connection
        connection_ok = test_gemini_connection()

        if not connection_ok:
            show_fix_instructions()
    else:
        show_fix_instructions()

    print()
    print("=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
