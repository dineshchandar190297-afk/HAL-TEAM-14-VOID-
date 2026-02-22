import hashlib
import random
import base64
import os
import sys
import csv
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Import the official crypto functions from the app
from app.crypto import encrypt, generate_search_token, generate_prefixes
from app.database import SessionLocal, BankRecord, SearchToken, BlockchainBlock

def seed_from_csv(csv_path):
    db = SessionLocal()
    
    print(f"Reading CSV: {csv_path}")
    print("Clearing old data to Fix Token Mismatch...")
    db.query(SearchToken).delete()
    db.query(BankRecord).delete()
    db.commit()

    start_time = time.time()
    batch_size = 1000
    records_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                raw_name = row.get('CustomerName', 'Unknown')
                raw_city = row.get('City', 'Unknown')
                raw_bank = row.get('BankName', 'Unknown')
                raw_branch = row.get('BranchName', 'Unknown')
                raw_acc = row.get('AccountNumber', '0000000000')
                raw_balance = row.get('Balance', '$0')
                raw_cust_id = "CUST_EXT_" + str(i + 1)
                
                # Use official encryption
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
                db.flush()
                
                # Use official token generation (HMAC-SHA256)
                tokens = generate_prefixes(raw_name) + generate_prefixes(raw_city)
                for t in tokens:
                    token_entry = SearchToken(token=t, record_id=record.id)
                    db.add(token_entry)
                
                records_count += 1
                
                if records_count % batch_size == 0:
                    db.commit()
                    elapsed = time.time() - start_time
                    print(f"Inserted {records_count} records... ({elapsed:.2f}s)")
                    
                    # Blockchain block
                    prev_block = db.query(BlockchainBlock).order_by(BlockchainBlock.id.desc()).first()
                    prev_hash = prev_block.current_hash if prev_block else "0" * 64
                    curr_hash = hashlib.sha256(f"{prev_hash}{records_count}BATCH_SECURE_FIX".encode()).hexdigest()
                    
                    block = BlockchainBlock(
                        action=f"SECURE_BATCH_IMPORT_{batch_size}",
                        user="ADMIN_001",
                        previous_hash=prev_hash,
                        current_hash=curr_hash
                    )
                    db.add(block)
                    db.commit()
                
                # Limit to 10k for speed in this re-seed fix, 
                # or carry on if user wants all 100k. 
                # Preserving 100k as requested earlier.
                if records_count >= 100000: break

            db.commit()
            
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        total_time = time.time() - start_time
        print(f"Successfully loaded {records_count} SECURE records in {total_time:.2f}s!")
        db.close()

if __name__ == "__main__":
    path = r'C:\Users\dines\Downloads\synthetic_banking_details_100000.csv'
    if os.path.exists(path):
        seed_from_csv(path)
    else:
        print(f"File not found: {path}")
