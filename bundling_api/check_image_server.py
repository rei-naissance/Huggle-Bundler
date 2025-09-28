#!/usr/bin/env python3
"""
Quick script to check if the local image server is ready
"""

import requests
import time

def check_server():
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Image Server Status:")
            print(f"   Status: {data.get('status')}")
            print(f"   Model Loaded: {data.get('model_loaded')}")
            print(f"   Device: {data.get('device')}")
            
            if data.get('model_loaded'):
                print("🎉 Server is ready for image generation!")
                return True
            else:
                print("⏳ Model is still loading...")
                return False
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to image server at http://localhost:8001")
        print("   Make sure to start it with: python local_image_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔌 Checking Local Image Server...")
    check_server()