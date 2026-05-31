const uploadForm = document.getElementById('upload-form');
const imageInput = document.getElementById('image-input');
const video = document.getElementById('video');
const captureBtn = document.getElementById('capture-btn');
const detectCamBtn = document.getElementById('detect-cam-btn');
const canvas = document.getElementById('canvas');
const outputImage = document.getElementById('output-image');
const info = document.getElementById('info');

async function postJson(url, body) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const error = await resp.json();
    throw new Error(error.detail || 'Request failed');
  }

  return resp.json();
}

async function postFormData(url, formData) {
  const resp = await fetch(url, { method: 'POST', body: formData });
  if (!resp.ok) {
    const error = await resp.json();
    throw new Error(error.detail || 'Upload failed');
  }
  return resp.json();
}

function showResult(result) {
  outputImage.src = result.image_data;

  if (result.detections.length === 0) {
    info.innerHTML = '<p>No objects detected.</p>';
    return;
  }

  const lines = result.detections.map(d =>
    `<li>${d.label} (${(d.confidence * 100).toFixed(1)}%)</li>`
  );
  info.innerHTML = '<strong>Detections:</strong><ul>' + lines.join('') + '</ul>';
}

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!imageInput.files || imageInput.files.length === 0) return;

  const formData = new FormData();
  formData.append('file', imageInput.files[0]);

  try {
    info.textContent = 'Detecting...';
    const result = await postFormData('/detect/image', formData);
    showResult(result);
  } catch (error) {
    info.textContent = 'Error: ' + error.message;
  }
});

captureBtn.addEventListener('click', () => {
  const context = canvas.getContext('2d');
  canvas.style.display = 'block';
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  detectCamBtn.disabled = false;
});

detectCamBtn.addEventListener('click', async () => {
  const dataUrl = canvas.toDataURL('image/jpeg');

  try {
    info.textContent = 'Detecting from webcam snapshot...';
    const result = await postJson('/detect/webcam', { image: dataUrl });
    showResult(result);
  } catch (error) {
    info.textContent = 'Error: ' + error.message;
  }
});

async function startWebcam() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
  } catch (error) {
    info.textContent = 'Webcam not available: ' + error.message;
  }
}

startWebcam();
