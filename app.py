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
