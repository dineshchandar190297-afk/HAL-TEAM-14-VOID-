from datetime import datetime, timedelta
import os
import sys
import random
import hashlib

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal, AuditLog

def simulate_traffic():
    db = SessionLocal()
    print("Simulating live traffic for graph...")
    
    # Use UTC for consistency
    now = datetime.utcnow()
    
    # Create 100 SEARCH events in the last 15 minutes
    # Spread them out
    for i in range(100):
        ts = now - timedelta(seconds=random.randint(0, 900))
        user = "admin"
        action = "SEARCH"
        details = f"Stress test query {i} - Automated Simulation"
        
        log = AuditLog(
            user=user,
            action=action,
            details=details,
            timestamp=ts,
            hash=hashlib.sha256(f"{action}{details}{user}{ts}".encode()).hexdigest()
        )
        db.add(log)
    
    db.commit()
    print(f"Successfully injected 100 Search logs at {now} UTC")
    db.close()

if __name__ == "__main__":
    simulate_traffic()
