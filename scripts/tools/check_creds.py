import psycopg2
import sys

passwords = ["postgres", "password", "admin", "root", "1234", "123456", ""]
user = "postgres"
host = "localhost"
port = 5432
dbname = "job_board" # Assuming this is the DB name from .env

print(f"Testing connections to {host}:{port} db={dbname} user={user}...")

success = False
for pwd in passwords:
    try:
        conn_str = f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"
        conn = psycopg2.connect(conn_str)
        conn.close()
        print(f"SUCCESS! Password is: '{pwd}'")
        success = True
        break
    except psycopg2.OperationalError as e:
        msg = str(e).strip()
        if "password authentication failed" in msg:
            print(f"Failed: '{pwd}' (Auth failed)")
        elif "database \"job_board\" does not exist" in msg:
             print(f"Auth OK but DB missing for password: '{pwd}'")
             # This means password IS correct!
             print(f"SUCCESS! Password is: '{pwd}' (But DB 'job_board' missing)")
             success = True
             break
        else:
            print(f"Failed: '{pwd}' - {msg}")

if not success:
    print("Could not connect with any common password.")
    sys.exit(1)
