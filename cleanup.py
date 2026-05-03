import os

files_to_remove = [
    'docker-compose.yml',
    'db/seed.sql'
]

for f in files_to_remove:
    if os.path.exists(f):
        os.remove(f)
        print(f"Removed {f}")
