import sys
import os
import warnings
import time

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=UserWarning)
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except ImportError:
    pass

from core.engine import JarvisEngine

def main():
    print("Initializing JARVIS Brain and Voice Systems...")
    
    # Initialize Engine in headless mode (no UI)
    engine = JarvisEngine(ui_window=None)
    engine.start()
    
    print("\n" + "="*50)
    print("JARVIS IS ONLINE")
    print("Listening for 'Hey Jarvis'...")
    print("Press Ctrl+C to shut down.")
    print("="*50 + "\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down JARVIS...")
        engine.stop()
        print("JARVIS is offline.")

if __name__ == "__main__":
    main()
