import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db, seed_enterprise_data

from api.auth import router as auth_router
from api.admin import router as admin_router
from api.teacher import router as teacher_router
from api.student import router as student_router
from api.ai import router as ai_router
from api.groups import router as groups_router
from api.proctoring import router as proctoring_router
from api.tests import router as tests_router

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

app = FastAPI(
    title="Enterprise Test & Imtihon Platformasi",
    description="Admin, O'qituvchi va O'quvchi rollari bilan jihozlangan ko'p bosqichli LMS & AI tahlil tizimi",
    version="2.0.0"
)

# CORS sozlamalari (xavfsiz va spetsifikatsiyaga mos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routerlarini ulash
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(teacher_router)
app.include_router(student_router)
app.include_router(ai_router)
app.include_router(groups_router)
app.include_router(proctoring_router)
app.include_router(tests_router)

# Statik fayllar
static_dir = BASE_DIR / "static"
os.makedirs(static_dir / "css", exist_ok=True)
os.makedirs(static_dir / "js", exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates_dir = BASE_DIR / "templates"
os.makedirs(templates_dir, exist_ok=True)

# ------------------ FRONTEND SAHIFALARI ------------------
@app.get("/", response_class=FileResponse)
def root_page():
    return FileResponse(str(templates_dir / "login.html"))

@app.get("/login", response_class=FileResponse)
def login_page():
    return FileResponse(str(templates_dir / "login.html"))

@app.get("/admin", response_class=FileResponse)
def admin_page():
    return FileResponse(str(templates_dir / "admin.html"))

@app.get("/teacher", response_class=FileResponse)
def teacher_page():
    return FileResponse(str(templates_dir / "teacher.html"))

@app.get("/student", response_class=FileResponse)
def student_page():
    return FileResponse(str(templates_dir / "student.html"))

@app.get("/exam/{test_id}", response_class=FileResponse)
def exam_page(test_id: int):
    return FileResponse(str(templates_dir / "exam.html"))

@app.get("/result/{session_id}", response_class=FileResponse)
def result_page(session_id: int):
    return FileResponse(str(templates_dir / "result.html"))

# ------------------ ISHGA TUSHISH ------------------
@app.on_event("startup")
def startup_event():
    init_db(force_recreate=False)
    seed_enterprise_data()
    print("Enterprise Test Platformasi tayyor!")

if __name__ == "__main__":
    import uvicorn
    import socket

    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    target_port = int(os.getenv("PORT", 8000))
    if is_port_in_use(target_port):
        alt_port = 8008 if not is_port_in_use(8008) else 8080
        print(f"Diqqat: {target_port}-port band. Server {alt_port}-portda ishga tushirilmoqda.")
        target_port = alt_port

    print(f"\n=======================================================")
    print(f"  Enterprise Test Platformasi: http://127.0.0.1:{target_port}")
    print(f"  Login Sahifasi:             http://127.0.0.1:{target_port}/login")
    print(f"  Admin Paneli:               http://127.0.0.1:{target_port}/admin")
    print(f"  O'qituvchi Kabineti:        http://127.0.0.1:{target_port}/teacher")
    print(f"  O'quvchi Kabineti:          http://127.0.0.1:{target_port}/student")
    print(f"  API Docs (Swagger):         http://127.0.0.1:{target_port}/docs")
    print(f"=======================================================\n")
    # Ishchi rejimda qotishlarning oldini olish uchun reload sozlanuvchi qilinadi
    should_reload = os.getenv("RELOAD", "false").lower() in ("true", "1")
    uvicorn.run("main:app", host="127.0.0.1", port=target_port, reload=should_reload)
