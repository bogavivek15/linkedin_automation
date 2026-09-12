import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apps.api.app.main import app as fastapi_app
import gradio as gr

def status():
    return "CareerOS Backend API is running. The FastAPI endpoints are available at the root URL."

# Create a minimal Gradio interface to satisfy Hugging Face's Gradio SDK
demo = gr.Interface(
    fn=status, 
    inputs=None, 
    outputs="text",
    title="CareerOS API",
    description="This is the backend API for CareerOS. The actual FastAPI routes are mounted and active."
)

# Mount the Gradio app at /ui, leaving the root (/) and /api/* for FastAPI
app = gr.mount_gradio_app(fastapi_app, demo, path="/ui")

if __name__ == "__main__":
    import uvicorn
    import time
    
    # Hugging Face sets the PORT environment variable (default 7860)
    port = int(os.environ.get("PORT", 7860))
    
    print(f"Starting Uvicorn on port {port}...")
    
    # Add a resilient retry loop in case the port is held by a stale crashed process
    for i in range(5):
        try:
            uvicorn.run(app, host="0.0.0.0", port=port)
            break
        except OSError as e:
            if "address already in use" in str(e).lower():
                print(f"Port {port} is in use. Waiting for stale process to release it... ({i+1}/5)")
                time.sleep(3)
            else:
                raise e
