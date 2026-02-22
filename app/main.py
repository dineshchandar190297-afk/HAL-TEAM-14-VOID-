import csv
import io
import time
import hashlib
import base64
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import os
from typing import Optional
import pyotp
import qrcode
import cv2
import numpy as np
from io import BytesIO

from app.database import (SessionLocal, BankRecord, SearchToken, init_db,
                           AuditLog, BlockchainBlock, UserActivity)
from app.crypto import (encrypt, decrypt_server, generate_search_token,
                         generate_prefixes, calculate_block_hash)
from app.auth import create_access_token, get_current_user, verify_password, get_password_hash, get_db, User
from app.email_utils import send_login_success_email, send_failed_login_email

app = FastAPI(title="HAL 4.0 — Secure Search Intelligence")
init_db()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ===== BLOCKCHAIN HELPER =====
def add_block(db: Session, user: str, action: str, details: str):
    """Create audit log + blockchain block for every action"""
    # Audit log
    log = AuditLog(user=user, action=action, details=details,
                   hash=hashlib.sha256(f"{action}{details}{user}".encode()).hexdigest())
    db.add(log)

    # Blockchain block
    last = db.query(BlockchainBlock).order_by(BlockchainBlock.id.desc()).first()
    prev_hash = last.current_hash if last else "GENESIS_" + "0" * 56
    ts = datetime.utcnow()
    curr_hash = calculate_block_hash(prev_hash, action, ts, user)
    db.add(BlockchainBlock(action=action, user=user, timestamp=ts,
                           previous_hash=prev_hash, current_hash=curr_hash))

    # Activity tracker
    act = db.query(UserActivity).filter(UserActivity.user == user).first()
    if not act:
        act = UserActivity(user=user)
        db.add(act)

    if action == "SEARCH":
        act.search_count += 1
        if act.search_count > 50:
            act.risk_score = min(100, act.risk_score + 8)
        elif act.search_count > 20:
            act.risk_score = min(100, act.risk_score + 3)
    act.last_action_time = ts
    db.commit()


# ===== AUTH =====
class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class TOTPVerify(BaseModel):
    code: str

class FaceLoginRequest(BaseModel):
    image: str # Base64 string
    username: Optional[str] = "admin"

@app.post("/register")
async def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_pwd, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    add_block(db, user.username, "REGISTER", f"Account created for {user.username}")
    return {"message": "Registration successful", "user": user.username}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                totp_code: str = Query(default=None),
                db: Session = Depends(get_db)):
    # Search by username OR email
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Track failed login attempts & send alert email
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            db.commit()
            send_failed_login_email(user.email, user.username, user.failed_login_attempts)
            add_block(db, form_data.username, "FAILED_LOGIN",
                      f"Failed attempt #{user.failed_login_attempts} — alert triggered")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Check if 2FA is enabled
    if user.totp_enabled and user.totp_secret:
        if not totp_code:
            return {"requires_2fa": True, "message": "TOTP code required"}
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=5):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    # If user is 'admin', force Face ID after 2FA/Password
    if user.username == "admin":
        return {"requires_face": True, "username": user.username, "message": "Biometric verification required"}

    # Successful login for normal users — reset failed attempts & send notification
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    send_login_success_email(user.email, user.username)
    token = create_access_token(data={"sub": user.username})
    add_block(db, user.username, "LOGIN", "JWT + 2FA authentication successful" if user.totp_enabled else "JWT authentication successful")
    return {"access_token": token, "token_type": "bearer", "totp_enabled": bool(user.totp_enabled)}


@app.post("/face-login")
async def face_login(req: FaceLoginRequest, db: Session = Depends(get_db)):
    """Expert-level biometric authentication via OpenCV"""
    try:
        # Load model and cascade
        if not os.path.exists("admin_face_model.yml"):
            raise HTTPException(status_code=400, detail="Face model not trained. Please run training script.")
        
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read("admin_face_model.yml")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # Decode base64 image
        header, encoded = req.image.split(",", 1)
        data = base64.b64decode(encoded)
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray) # Match training preprocessing

        # Detect face
        faces = face_cascade.detectMultiScale(gray, 1.2, 6)
        
        if len(faces) == 0:
            raise HTTPException(status_code=401, detail="No face detected. Please position yourself clearly in the frame.")
        
        if len(faces) > 1:
            add_block(db, req.username or "admin", "FACE_SECURITY_ALERT", "Multiple faces detected during biometric login")
            raise HTTPException(status_code=401, detail="Security Violation: Multiple faces detected. Only one person should be in the frame.")

        for (x, y, w, h) in faces:
            id_, confidence = recognizer.predict(gray[y:y+h, x:x+w])
            print(f"[FACE DEBUG] Predicted ID: {id_}, Confidence: {confidence}")
            
            # LBPH confidence: lower is better. 58 is a very strict "95% accuracy" threshold.
            if id_ == 1 and confidence < 58:
                user = db.query(User).filter(User.username == (req.username or "admin")).first()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found in database")
                
                # Final Success Step for Admin
                user.failed_login_attempts = 0
                user.last_login = datetime.utcnow()
                db.commit()
                
                if user.email:
                    send_login_success_email(user.email, user.username)
                
                token = create_access_token(data={"sub": user.username})
                add_block(db, user.username, "FACE_LOGIN", f"Biometric verification successful (conf: {round(confidence, 2)})")
                
                return {
                    "access_token": token, 
                    "token_type": "bearer", 
                    "totp_enabled": bool(user.totp_enabled),
                    "confidence": round(confidence, 2)
                }
        
        # If we reached here, face was detected but confidence was too high (bad match)
        raise HTTPException(status_code=401, detail="Face ID didn't match. Biometric verification failed.")

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Face Login Error: {e}")
        raise HTTPException(status_code=500, detail="Biometric processing failed")


# ===== 2FA SETUP =====
@app.get("/2fa-status")
async def twofa_status(current_user: User = Depends(get_current_user)):
    return {"enabled": bool(current_user.totp_enabled)}

@app.post("/setup-2fa")
async def setup_2fa(db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Generate a new TOTP secret and return QR code as base64 PNG"""
    secret = pyotp.random_base32()
    # Store secret (not yet enabled until verified)
    current_user.totp_secret = secret
    db.commit()
    # Generate provisioning URI
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.username, issuer_name="HAL 4.0")
    # Generate QR code as base64
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return {"secret": secret, "qr_code": qr_b64, "uri": uri}

@app.post("/enable-2fa")
async def enable_2fa(body: TOTPVerify,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """Verify the TOTP code and enable 2FA"""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Run /setup-2fa first")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(body.code, valid_window=5):
        raise HTTPException(status_code=401, detail="Invalid code. Try again.")
    current_user.totp_enabled = 1
    db.commit()
    add_block(db, current_user.username, "2FA_ENABLED", "Google Authenticator activated")
    return {"message": "2FA enabled successfully", "enabled": True}

@app.post("/disable-2fa")
async def disable_2fa(body: TOTPVerify,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    """Disable 2FA after verifying current code"""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not set up")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(body.code, valid_window=5):
        raise HTTPException(status_code=401, detail="Invalid code")
    current_user.totp_enabled = 0
    current_user.totp_secret = None
    db.commit()
    add_block(db, current_user.username, "2FA_DISABLED", "Google Authenticator deactivated")
    return {"message": "2FA disabled", "enabled": False}


# ===== STATS =====
@app.get("/stats")
async def stats(db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return {
        "total_records": db.query(BankRecord).count(),
        "total_tokens": db.query(SearchToken).count(),
        "total_blocks": db.query(BlockchainBlock).count(),
        "total_logs": db.query(AuditLog).count(),
    }


# ===== SECURE SEARCH (THE CORE PS) =====
@app.post("/secure-search")
async def secure_search(query: str,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    t0 = time.time()
    token = generate_search_token(query)
    matches = db.query(SearchToken).filter(SearchToken.token == token).limit(50).all()

    results = []
    seen = set()
    for m in matches:
        if m.record_id not in seen:
            r = m.record
            results.append({
                "id": r.id,
                "customer_name": r.customer_name,
                "account": r.account_number,
                "city": r.city,
                "bank": r.bank_name,
                "branch": r.branch,
            })
            seen.add(m.record_id)

    elapsed = round((time.time() - t0) * 1000, 2)
    add_block(db, current_user.username, "SEARCH",
              f"query_token={token[:16]}... results={len(results)} time={elapsed}ms")
    return {"results": results, "token": token, "time_ms": elapsed, "count": len(results)}


# ===== BLOCKCHAIN — TAMPER CHECK =====
@app.get("/tamper-check")
async def tamper_check(db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    blocks = db.query(BlockchainBlock).order_by(BlockchainBlock.id.asc()).all()
    prev = "GENESIS_" + "0" * 56
    for b in blocks:
        expected = calculate_block_hash(prev, b.action, b.timestamp, b.user)
        if b.current_hash != expected:
            return {"status": "TAMPER_DETECTED", "block_id": b.id, "total": len(blocks)}
        prev = b.current_hash
    return {"status": "VERIFIED", "total": len(blocks), "last_hash": prev[:32] + "..."}


# ===== BLOCKCHAIN — GET CHAIN =====
@app.get("/blockchain-chain")
async def get_chain(db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    blocks = db.query(BlockchainBlock).order_by(BlockchainBlock.id.desc()).limit(50).all()
    return [{"id": b.id, "time": str(b.timestamp)[:19], "action": b.action,
             "user": b.user, "prev": b.previous_hash[:16] + "...",
             "hash": b.current_hash[:16] + "..."} for b in blocks]


# ===== AUDIT LOGS =====
@app.get("/audit-logs")
async def audit_logs(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [{"id": l.id, "time": str(l.timestamp)[:19], "user": l.user,
             "action": l.action, "details": l.details, "hash": l.hash[:16] + "..."}
            for l in logs]


# ===== ANOMALY DETECTION =====
@app.get("/anomaly-report")
async def anomaly_report(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    activities = db.query(UserActivity).all()
    alerts = []
    for a in activities:
        level = "NORMAL"
        if a.risk_score > 70:
            level = "CRITICAL"
            alerts.append(f"User '{a.user}': Data scraping behavior (score {a.risk_score})")
        elif a.risk_score > 30:
            level = "WARNING"
            alerts.append(f"User '{a.user}': Unusual search frequency (score {a.risk_score})")

    # Search frequency timeline (last 10 minutes)
    now = datetime.utcnow().replace(second=0, microsecond=0)
    timeline = []
    for i in range(12): # Show 12 points for better resolution
        t = now - timedelta(minutes=11 - i)
        c = db.query(AuditLog).filter(
            AuditLog.action == "SEARCH",
            AuditLog.timestamp >= t,
            AuditLog.timestamp < t + timedelta(minutes=1)
        ).count()
        timeline.append({"label": t.strftime("%H:%M"), "count": c})

    return {
        "users": [{"user": a.user, "searches": a.search_count,
                    "score": a.risk_score, "last": str(a.last_action_time)[:19]}
                   for a in activities],
        "alerts": alerts,
        "timeline": timeline
    }


# ===== PERFORMANCE METRICS =====
@app.get("/performance-metrics")
async def perf_metrics(db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    # Run a live encryption benchmark
    t0 = time.time()
    for _ in range(100):
        encrypt("benchmark-test-string-12345")
    enc_time = round((time.time() - t0) / 100 * 1000, 3)

    # Run a live search benchmark
    t0 = time.time()
    for _ in range(100):
        generate_search_token("benchmark")
    tok_time = round((time.time() - t0) / 100 * 1000, 3)

    total_rec = db.query(BankRecord).count()
    total_tok = db.query(SearchToken).count()

    return {
        "enc_speed_ms": enc_time,
        "token_speed_ms": tok_time,
        "total_records": total_rec,
        "total_tokens": total_tok,
        "tokens_per_record": round(total_tok / max(total_rec, 1), 1),
        "throughput_est": round(1000 / max(enc_time, 0.001)),
    }


# ===== CSV UPLOAD =====
def process_csv(content: str, user: str):
    db = SessionLocal()
    try:
        reader = csv.DictReader(io.StringIO(content))
        count = 0
        for row in reader:
            rec = BankRecord(
                customer_id=encrypt(row.get('customer_id', '')),
                customer_name=encrypt(row.get('customer_name', '')),
                account_number=encrypt(row.get('account_number', '')),
                bank_name=encrypt(row.get('bank_name', '')),
                branch=encrypt(row.get('branch', '')),
                city=encrypt(row.get('city', '')),
                balance=encrypt(row.get('balance', '0'))
            )
            db.add(rec)
            db.flush()
            for t in set(generate_prefixes(row.get('customer_name', '')) +
                         generate_prefixes(row.get('city', ''))):
                db.add(SearchToken(token=t, record_id=rec.id))
            count += 1
        db.commit()
        add_block(db, user, "CSV_UPLOAD", f"{count} records encrypted and indexed")
    except Exception as e:
        db.rollback()
    finally:
        db.close()


@app.post("/upload-csv")
async def upload_csv(bg: BackgroundTasks, file: UploadFile = File(...),
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    content = (await file.read()).decode('utf-8')
    add_block(db, current_user.username, "CSV_UPLOAD_START", file.filename)
    bg.add_task(process_csv, content, current_user.username)
    return {"message": "Processing started"}


# ===== BREACH SIMULATION =====
@app.get("/breach-simulation")
async def breach(db: Session = Depends(get_db)):
    recs = db.query(BankRecord).limit(15).all()
    return {"dump": [{"id": r.id, "name": r.customer_name[:40] + "...",
                      "acc": r.account_number[:40] + "...",
                      "city": r.city[:40] + "..."} for r in recs]}


# ===== SERVE FRONTEND =====
@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"))