from ..firebase.firestore import db_firestore
from ..models.db import get_db_conn
import psycopg2.extras

SYNC_TABLES = ['customers', 'accounts', 'transactions', 'loans']

def postgres_to_firebase():
    """Backup: Postgres -> Firestore"""
    if db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    sync_results = {}
    for table in SYNC_TABLES:
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        
        batch = db_firestore.batch()
        col_ref = db_firestore.collection(table)
        
        count = 0
        for row in rows:
            # Convert values to strings for Firestore compatibility if needed
            doc_data = {k: str(v) if v is not None else None for k, v in row.items()}
            # Use the first column (usually ID) as the document ID
            pk_col = list(row.keys())[0]
            doc_ref = col_ref.document(str(row[pk_col]))
            batch.set(doc_ref, doc_data)
            count += 1
        
        if count > 0:
            batch.commit()
        sync_results[table] = count
    
    return {"status": "success", "synced": sync_results}

def firebase_to_postgres():
    """Restore: Firestore -> Postgres"""
    if db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    restore_results = {}
    for table in SYNC_TABLES:
        docs = db_firestore.collection(table).stream()
        count = 0
        for doc in docs:
            data = doc.to_dict()
            columns = data.keys()
            placeholders = [f"%({col})s" for col in columns]
            
            # Upsert logic
            sql = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT DO NOTHING
            """
            cur.execute(sql, data)
            count += 1
        
        conn.commit()
        restore_results[table] = count
        
    return {"status": "success", "restored": restore_results}
