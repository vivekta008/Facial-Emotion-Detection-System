from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ultralytics import YOLO
import cv2
import numpy as np
import base64
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Facial Emotion Detection System")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Load the YOLO model
model = YOLO(str(BASE_DIR / "best.pt"))


class WebcamPayload(BaseModel):
    image: str



def run_detection(cv_image: np.ndarray):
    # YOLO expects BGR or RGB; cv2 returns BGR
    results = model.predict(source=cv_image, conf=0.25, imgsz=640, verbose=False)
    if len(results) == 0:
        raise HTTPException(status_code=500, detail="Model inference failed.")
    r = results[0]

    detections = []
    if r.boxes is not None and len(r.boxes) > 0:
        xyxy = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy().astype(int)
        for (x1, y1, x2, y2), conf, cls in zip(xyxy, confs, classes):
            detections.append({
                "label": model.names.get(cls, str(cls)),
                "confidence": float(conf),
                "box": [float(x1), float(y1), float(x2), float(y2)],
            })

    annotated = r.plot() if hasattr(r, "plot") else cv_image
    if annotated is None:
        annotated = cv_image

    # Encode annotated image as base64 string for easy HTML display
    _, buffer = cv2.imencode('.jpg', annotated)
    image_base64 = base64.b64encode(buffer).decode('utf-8')

    return {
        "detections": detections,
        "image_data": f"data:image/jpeg;base64,{image_base64}",
    }



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )



@app.post("/detect/image")
async def detect_image(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    result = run_detection(image)
    return JSONResponse(result)




@app.post("/detect/webcam")
async def detect_webcam(payload: WebcamPayload):
    img_data = payload.image
    if img_data.startswith("data:"):
        img_data = img_data.split(",", 1)[1]

    try:
        decoded = base64.b64decode(img_data)
        nparr = np.frombuffer(decoded, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image data")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webcam image: {e}")

    result = run_detection(image)
    return JSONResponse(result)



if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0"
    port = 8000
    print(f"Starting Facial Emotion Detection app on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=True)
