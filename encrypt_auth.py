import os
import sys
import json
from cryptography.fernet import Fernet

def encrypt_file(file_path, output_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return None

    # Generate a key
    key = Fernet.generate_key()
    fernet = Fernet(key)

    with open(file_path, 'rb') as f:
        data = f.read()

    # Validate JSON
    try:
        json.loads(data)
    except json.JSONDecodeError:
        print(f"Error: {file_path} is not a valid JSON file.")
        return None

    encrypted_data = fernet.encrypt(data)

    with open(output_path, 'wb') as f:
        f.write(encrypted_data)

    return key.decode()

def main():
    input_file = 'browser.json'
    output_file = 'browser.json.enc'

    print(f"Encrypting {input_file} to {output_file}...")
    key = encrypt_file(input_file, output_file)

    if key:
        print("\nSuccess! File encrypted.")
        print("-" * 40)
        print("YOUR ENCRYPTION KEY (SAVE THIS!):")
        print(key)
        print("-" * 40)
        print("\nAdd this key to your GitHub Secrets as: YTMUSIC_AUTH_KEY")
        print("Then you can safely commit 'browser.json.enc' to your repository.")
        print("Note: Do NOT commit your original 'browser.json' or share the key.")

if __name__ == "__main__":
    main()
