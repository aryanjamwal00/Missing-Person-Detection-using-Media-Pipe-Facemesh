#!/usr/bin/env python3
"""
Utility script to generate secure secret keys for the application.
Run this script to generate a strong SECRET_KEY for your .env file.
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages.helper.config_manager import SecretManager


def main():
    """Generate and display a secure secret key."""
    print("🔐 Generating secure secret key...")
    print("=" * 50)
    
    # Generate a 32-byte (256-bit) secret key
    secret_key = SecretManager.generate_secret_key(length=32)
    
    print(f"Generated SECRET_KEY: {secret_key}")
    print("=" * 50)
    print("\n📝 Add this to your .env file:")
    print(f"SECRET_KEY={secret_key}")
    print("\n⚠️  Keep this key secret and never commit it to version control!")
    print("=" * 50)
    
    # Validate the key strength
    if SecretManager.validate_secret_strength(secret_key):
        print("✅ Secret key meets strength requirements")
    else:
        print("❌ Secret key does not meet strength requirements (this shouldn't happen)")
    
    return secret_key


if __name__ == "__main__":
    main()