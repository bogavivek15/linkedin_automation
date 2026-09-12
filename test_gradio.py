from fastapi import FastAPI
import gradio as gr

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

demo = gr.Interface(lambda x: x, "text", "text")
app = gr.mount_gradio_app(app, demo, path="/ui")
