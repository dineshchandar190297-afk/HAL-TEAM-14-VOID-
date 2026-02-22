from app.database import SessionLocal, BankRecord, SearchToken
from app.crypto import decrypt_server, generate_prefixes
import sys

def reindex():
    db = SessionLocal()
    try:
        print("Starting re-indexing of all records to support single-letter search...")
        records = db.query(BankRecord).all()
        total = len(records)
        print(f"Found {total} records. This might take a moment.")
        
        # Clear existing tokens to avoid duplicates and ensure consistency
        db.query(SearchToken).delete()
        db.commit()
        
        tokens_to_add = []
        count = 0
        for r in records:
            try:
                name = decrypt_server(r.customer_name)
                city = decrypt_server(r.city)
                
                tokens = set(generate_prefixes(name) + generate_prefixes(city))
                
                for t in tokens:
                    tokens_to_add.append({"token": t, "record_id": r.id})
                
                count += 1
                if len(tokens_to_add) >= 5000:
                    db.bulk_insert_mappings(SearchToken, tokens_to_add)
                    db.commit()
                    tokens_to_add = []
                    sys.stdout.write(f"\rProcessed {count}/{total} records... Items indexed: {count * 5}")
                    sys.stdout.flush()
            except Exception as e:
                continue
                
        if tokens_to_add:
            db.bulk_insert_mappings(SearchToken, tokens_to_add)
            db.commit()
            
        print(f"\nRe-indexing complete. Processed {count} records.")
        print(f"\nRe-indexing complete. Processed {count} records.")
    except Exception as e:
        print(f"\nCritical Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reindex()
