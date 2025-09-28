#!/usr/bin/env python3
"""
Start the async image generation server
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    print("🚀 Starting Async Local Image Generation Server")
    print("=" * 60)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    server_script = script_dir / "local_image_server_async.py"
    
    if not server_script.exists():
        print(f"❌ Server script not found: {server_script}")
        sys.exit(1)
    
    try:
        # Start the server
        print("Starting server...")
        print(f"Script path: {server_script}")
        print("Server will be available at: http://localhost:8001")
        print("Use Ctrl+C to stop the server")
        print("=" * 60)
        
        # Run the server
        subprocess.run([
            sys.executable, str(server_script)
        ], cwd=str(script_dir))
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()