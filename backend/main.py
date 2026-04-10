from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
import os

from database import engine, get_db, Base
from models import User, Project, CodeGeneration
from schemas import (
    UserCreate, UserLogin, UserOut,
    ProjectCreate, ProjectOut,
    CodeGenRequest, CodeGenOut,
    Token
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EmbedCV Workshop API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "embedcv-super-secret-key-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ──────────────────────────────────────────
#  AUTH ROUTES
# ──────────────────────────────────────────
@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = bcrypt.hashpw(user_in.password.encode(), bcrypt.gensalt()).decode()
    user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed,
        institution=user_in.institution
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not bcrypt.checkpw(credentials.password.encode(), user.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ──────────────────────────────────────────
#  PROJECT ROUTES
# ──────────────────────────────────────────
@app.get("/projects", response_model=list[ProjectOut])
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()


@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        target_mcu=project_in.target_mcu,
        user_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


# ──────────────────────────────────────────
#  CODE GENERATION ROUTES
# ──────────────────────────────────────────
@app.post("/generate", response_model=CodeGenOut, status_code=201)
def generate_code(
    req: CodeGenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project ownership
    project = db.query(Project).filter(Project.id == req.project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Simulate hardware-aware code generation (replace with real LLM call)
    generated = _simulate_code_generation(req.prompt, req.target_mcu, req.language)

    codegen = CodeGeneration(
        project_id=req.project_id,
        prompt=req.prompt,
        target_mcu=req.target_mcu,
        language=req.language,
        generated_code=generated["code"],
        ram_estimate_kb=generated["ram_kb"],
        flash_estimate_kb=generated["flash_kb"],
        energy_estimate_mw=generated["energy_mw"],
        time_complexity=generated["time_complexity"],
        compilation_status=generated["compilation_status"],
        compilation_notes=generated["notes"],
    )
    db.add(codegen)
    db.commit()
    db.refresh(codegen)
    return codegen


@app.get("/projects/{project_id}/generations", response_model=list[CodeGenOut])
def get_generations(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(CodeGeneration).filter(CodeGeneration.project_id == project_id).order_by(CodeGeneration.created_at.desc()).all()


@app.get("/generations/{gen_id}", response_model=CodeGenOut)
def get_generation(gen_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    gen = db.query(CodeGeneration).filter(CodeGeneration.id == gen_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    return gen


# ──────────────────────────────────────────
#  STATS ROUTE
# ──────────────────────────────────────────
@app.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_projects = db.query(Project).filter(Project.user_id == current_user.id).count()
    total_generations = db.query(CodeGeneration).join(Project).filter(Project.user_id == current_user.id).count()
    successful = db.query(CodeGeneration).join(Project).filter(
        Project.user_id == current_user.id,
        CodeGeneration.compilation_status == "success"
    ).count()
    return {
        "total_projects": total_projects,
        "total_generations": total_generations,
        "successful_compilations": successful,
        "success_rate": round((successful / total_generations * 100) if total_generations > 0 else 0, 1)
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ──────────────────────────────────────────
#  SIMULATION ENGINE (Replace with real LLM)
# ──────────────────────────────────────────
def _simulate_code_generation(prompt: str, target_mcu: str, language: str) -> dict:
    mcu_profiles = {
        "STM32": {"ram": 512, "flash": 1024, "voltage": 3.3},
        "ESP32": {"ram": 520, "flash": 4096, "voltage": 3.3},
        "ESP32-CAM": {"ram": 520, "flash": 4096, "voltage": 3.3},
        "Raspberry Pi": {"ram": 1024000, "flash": 32000000, "voltage": 5.0},
        "Arduino": {"ram": 2, "flash": 32, "voltage": 5.0},
        "Arduino Nano": {"ram": 2, "flash": 32, "voltage": 5.0},
    }
    profile = mcu_profiles.get(target_mcu, {"ram": 256, "flash": 512, "voltage": 3.3})

    import hashlib
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    ram_used = round(min((seed % 40 + 8) / 100 * profile["ram"], profile["ram"] * 0.85), 2)
    flash_used = round(min((seed % 30 + 12) / 100 * profile["flash"], profile["flash"] * 0.75), 2)
    energy_mw = round(profile["voltage"] * (10 + seed % 50) / 1000 * 1000, 2)

    complexities = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"]
    complexity = complexities[seed % len(complexities)]

    code_templates = {
        "C": _gen_c_code(target_mcu, prompt),
        "C++": _gen_cpp_code(target_mcu, prompt),
        "Python": _gen_python_code(target_mcu, prompt),
        "MicroPython": _gen_micropython_code(target_mcu, prompt),
        "Arduino": _gen_arduino_code(target_mcu, prompt),
    }

    code = code_templates.get(language, code_templates["C"])
    notes = f"Generated for {target_mcu}. RAM budget: {profile['ram']} KB, Flash budget: {profile['flash']} KB. Estimated usage: {ram_used} KB RAM, {flash_used} KB Flash."

    return {
        "code": code,
        "ram_kb": ram_used,
        "flash_kb": flash_used,
        "energy_mw": energy_mw,
        "time_complexity": complexity,
        "compilation_status": "success" if ram_used < profile["ram"] and flash_used < profile["flash"] else "warning",
        "notes": notes,
    }


def _gen_c_code(mcu: str, prompt: str) -> str:
    return f"""/**
 * EmbedCV Workshop - Generated Code
 * Target MCU: {mcu}
 * Task: {prompt[:60]}...
 * Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
 */

#include <stdint.h>
#include <stdbool.h>

#ifdef STM32
  #include "stm32f4xx_hal.h"
  #define LED_PIN GPIO_PIN_13
  #define LED_PORT GPIOC
#else
  #define LED_PIN 13
#endif

/* ── Configuration ── */
#define FRAME_WIDTH   320
#define FRAME_HEIGHT  240
#define THRESHOLD     128

/* ── Frame buffer (SRAM) ── */
static uint8_t frame_buf[FRAME_WIDTH * FRAME_HEIGHT];

/**
 * @brief Initialise camera peripheral
 * @return HAL status code
 */
int camera_init(void) {{
    /* TODO: Configure camera I2C/SPI interface */
    /* Set resolution, frame rate, pixel format  */
    return 0;
}}

/**
 * @brief Capture one frame into frame_buf
 * @return Number of bytes captured
 */
int capture_frame(uint8_t *buf, uint16_t width, uint16_t height) {{
    if (!buf) return -1;
    /* DMA transfer from camera FIFO → buf */
    for (uint32_t i = 0; i < (uint32_t)(width * height); i++) {{
        buf[i] = 0; /* placeholder pixel */
    }}
    return width * height;
}}

/**
 * @brief Simple threshold-based object detection  O(n)
 * @param buf   Grayscale frame buffer
 * @param size  Total pixels
 * @return Detected pixel count
 */
uint32_t detect_objects(const uint8_t *buf, uint32_t size) {{
    uint32_t count = 0;
    for (uint32_t i = 0; i < size; i++) {{
        if (buf[i] > THRESHOLD) count++;
    }}
    return count;
}}

int main(void) {{
#ifdef STM32
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
#endif

    if (camera_init() != 0) {{
        /* Blink error indicator */
        while (1) {{ /* error loop */ }}
    }}

    while (1) {{
        capture_frame(frame_buf, FRAME_WIDTH, FRAME_HEIGHT);
        uint32_t objects = detect_objects(frame_buf, FRAME_WIDTH * FRAME_HEIGHT);

        if (objects > 1000) {{
            /* Object detected — trigger output */
#ifdef STM32
            HAL_GPIO_TogglePin(LED_PORT, LED_PIN);
#endif
        }}

#ifdef STM32
        HAL_Delay(100);
#endif
    }}
    return 0;
}}
"""


def _gen_cpp_code(mcu: str, prompt: str) -> str:
    return f"""/**
 * EmbedCV Workshop — C++ Generated Code
 * Target: {mcu} | Task: {prompt[:50]}
 */

#include <cstdint>
#include <array>

constexpr uint16_t WIDTH  = 320;
constexpr uint16_t HEIGHT = 240;
constexpr uint8_t  THRESH = 128;

class FrameCapture {{
public:
    std::array<uint8_t, WIDTH * HEIGHT> buffer{{}};

    bool init() {{
        /* Initialise camera peripheral */
        return true;
    }}

    bool capture() {{
        /* Capture frame via DMA */
        buffer.fill(0);
        return true;
    }}
}};

class ObjectDetector {{
public:
    uint32_t detect(const uint8_t* buf, uint32_t size) {{
        uint32_t count = 0;
        for (uint32_t i = 0; i < size; ++i)
            if (buf[i] > THRESH) ++count;
        return count;
    }}
}};

int main() {{
    FrameCapture cam;
    ObjectDetector detector;

    if (!cam.init()) return 1;

    while (true) {{
        cam.capture();
        auto n = detector.detect(cam.buffer.data(), cam.buffer.size());
        /* Use n for further logic */
        (void)n;
    }}
}}
"""


def _gen_python_code(mcu: str, prompt: str) -> str:
    return f"""# EmbedCV Workshop - Python Generated Code
# Target: {mcu} | Task: {prompt[:50]}

import cv2
import numpy as np

WIDTH, HEIGHT = 320, 240
THRESHOLD = 128


def init_camera(device_id: int = 0) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(device_id)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    return cap


def detect_objects(frame: np.ndarray) -> int:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return len(contours)


def main():
    cap = init_camera()
    if not cap.isOpened():
        raise RuntimeError("Camera not available")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        count = detect_objects(frame)
        print(f"Objects detected: {{count}}")

    cap.release()


if __name__ == "__main__":
    main()
"""


def _gen_micropython_code(mcu: str, prompt: str) -> str:
    return f"""# EmbedCV Workshop - MicroPython Generated Code
# Target: {mcu} | Task: {prompt[:50]}

import machine
import utime

# Camera pin config (ESP32-CAM)
PWDN_PIN  = 32
RESET_PIN = -1
XCLK_PIN  = 0
SIOD_PIN  = 26
SIOC_PIN  = 27
Y9_PIN    = 35
Y8_PIN    = 34
Y7_PIN    = 39
Y6_PIN    = 36
Y5_PIN    = 21
Y4_PIN    = 19
Y3_PIN    = 18
Y2_PIN    = 5
VSYNC_PIN = 25
HREF_PIN  = 23
PCLK_PIN  = 22

led = machine.Pin(4, machine.Pin.OUT)

def blink(n=1, delay_ms=200):
    for _ in range(n):
        led.on()
        utime.sleep_ms(delay_ms)
        led.off()
        utime.sleep_ms(delay_ms)

def main():
    print("EmbedCV starting on {mcu}...")
    blink(3)

    while True:
        # Placeholder: replace with actual camera frame capture
        utime.sleep_ms(500)
        blink(1, 50)
        print("Frame captured")

main()
"""


def _gen_arduino_code(mcu: str, prompt: str) -> str:
    return f"""/**
 * EmbedCV Workshop - Arduino Generated Code
 * Target: {mcu} | Task: {prompt[:50]}
 */

const int LED_PIN = 13;
const int THRESHOLD = 128;

void setup() {{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("EmbedCV on {mcu} ready.");
}}

void loop() {{
  // Placeholder: read sensor / camera data
  int reading = analogRead(A0);

  if (reading > THRESHOLD) {{
    digitalWrite(LED_PIN, HIGH);
    Serial.print("Object detected: ");
    Serial.println(reading);
  }} else {{
    digitalWrite(LED_PIN, LOW);
  }}

  delay(100);
}}
"""


# ── SERVE FRONTEND (single service deployment) ──
from static_serve import mount_frontend
mount_frontend(app)
