import hashlib
import random
import base64
import os
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal, BankRecord, SearchToken, BlockchainBlock, AuditLog

# Key for demo
DEMO_KEY = hashlib.sha256(b"hackathon-secret-key").digest()[:16] # 128-bit AES

def encrypt(text: str) -> str:
    cipher = AES.new(DEMO_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(text.encode(), AES.block_size))
    return base64.b64encode(encrypted).decode()

def generate_tokens(text: str):
    text = text.lower().strip()
    tokens = []
    # Full word token
    tokens.append(hashlib.sha256(text.encode()).hexdigest())
    # Prefix tokens
    if len(text) > 2:
        for i in range(3, len(text) + 1):
            prefix = text[:i]
            tokens.append(hashlib.sha256(prefix.encode()).hexdigest())
    return list(set(tokens))

def seed_data():
    names = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Ananya", "Suresh", "Meera", "Arjun", "Kavita", 
             "John", "Sarah", "Michael", "Emma", "David", "Olivia", "James", "Sophia", "Robert", "Isabella"]
    cities = ["Chennai", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
              "New York", "London", "Tokyo", "Paris", "Berlin", "Sydney", "Singapore", "Dubai", "Toronto"]
    banks = ["HDFC", "ICICI", "SBI", "Axis", "Kotak", "HSBC", "Chase", "Barclays", "Revolut"]

    db = SessionLocal()
    
    print("Clearing old data...")
    db.query(SearchToken).delete()
    db.query(BankRecord).delete()
    db.commit()

    print("Generating 200 high-quality records...")
    
    for i in range(1, 201):
        raw_name = random.choice(names) + " " + random.choice(["Kumar", "Sharma", "Singh", "Patel", "Das", "Menon", "Smith", "Johnson"])
        raw_city = random.choice(cities)
        raw_bank = random.choice(banks)
        raw_branch = "Branch_" + str(random.randint(10, 99))
        raw_acc = str(random.randint(1000000000, 9999999999))
        raw_cust_id = "CUST_" + str(1000 + i)
        raw_balance = "$" + str(random.randint(1000, 99999))
        
        # Encyrpt sensitive parts
        enc_name = encrypt(raw_name)
        enc_city = encrypt(raw_city)
        enc_acc = encrypt(raw_acc)
        enc_balance = encrypt(raw_balance)
        
        record = BankRecord(
            customer_id=raw_cust_id,
            customer_name=enc_name,
            account_number=enc_acc,
            bank_name=raw_bank,
            branch=raw_branch,
            city=enc_city,
            balance=enc_balance
        )
        db.add(record)
        db.flush() # Get ID

        # Generate search tokens for Name and City
        tokens = generate_tokens(raw_name) + generate_tokens(raw_city)
        for t in tokens:
            token_entry = SearchToken(token=t, record_id=record.id)
            db.add(token_entry)
        
        # Add to Blockchain for every 10 records for simulation
        if i % 10 == 0:
            prev_block = db.query(BlockchainBlock).order_by(BlockchainBlock.id.desc()).first()
            prev_hash = prev_block.current_hash if prev_block else "0" * 64
            curr_hash = hashlib.sha256(f"{prev_hash}{i}BATCH_ADD".encode()).hexdigest()
            
            block = BlockchainBlock(
                action=f"BATCH_INSERT_10_RECORDS",
                user="SYSTEM",
                previous_hash=prev_hash,
                current_hash=curr_hash
            )
            db.add(block)
            
            print(f"Seeded {i} records...")
            db.commit()

    db.commit()
    print("Successfully seeded 200 high-fidelity encrypted records!")
    db.close()

if __name__ == "__main__":
    seed_data()
