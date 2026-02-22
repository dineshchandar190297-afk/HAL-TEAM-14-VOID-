import hashlib
import random
from datetime import datetime, timedelta
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal, AuditLog, UserActivity, BlockchainBlock

def bootstrap_intelligence():
    db = SessionLocal()
    print("Bootstrapping intelligence and activity logs...")
    
    # 1. Create some historical user activity
    users = ["ADMIN_001", "SEC_OFFICER_A", "DATA_ANALYST_B"]
    for username in users:
        act = db.query(UserActivity).filter(UserActivity.user == username).first()
        if not act:
            act = UserActivity(user=username)
            db.add(act)
        
        act.search_count = random.randint(150, 450)
        # Give one user a high risk score for the demo
        if username == "DATA_ANALYST_B":
            act.risk_score = 78.5
        else:
            act.risk_score = random.uniform(5.0, 15.0)
        act.last_action_time = datetime.utcnow() - timedelta(minutes=random.randint(1, 60))

    # 2. Create Search Logs for the last 60 minutes to fill the timeline chart
    now = datetime.utcnow()
    actions = ["SEARCH", "QUERY", "AUTH_VERIFY", "EXPORT_REPORT"]
    
    # Generate ~200 logs over the last hour
    for i in range(200):
        ts = now - timedelta(seconds=random.randint(0, 3600))
        user = random.choice(users)
        action = random.choice(actions)
        details = f"Query executed on encrypted index (AES-256) for token: {hashlib.sha256(str(i).encode()).hexdigest()[:8]}..."
        
        log = AuditLog(
            user=user,
            action=action,
            details=details,
            timestamp=ts,
            hash=hashlib.sha256(f"{action}{details}{user}{ts}".encode()).hexdigest()
        )
        db.add(log)

    db.commit()
    print("Intelligence data bootstrapped successfully!")
    db.close()

if __name__ == "__main__":
    bootstrap_intelligence()
