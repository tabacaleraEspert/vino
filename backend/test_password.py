import sys
sys.path.insert(0, '.')
from app.core.security import verify_password, hash_password

stored_hash = "$2b$12$wVR2w0tW0MlKULHmt/e2xO7T3iwlh/oEKOyKP7N8mitUCKfE1VDsW"
print("Testing password 'miPassword123':", verify_password("miPassword123", stored_hash))
print("Testing password 'mipassword123':", verify_password("mipassword123", stored_hash))

# Generate a new hash for the password to check
new_hash = hash_password("miPassword123")
print("New hash:", new_hash)
print("Verify new hash:", verify_password("miPassword123", new_hash))
