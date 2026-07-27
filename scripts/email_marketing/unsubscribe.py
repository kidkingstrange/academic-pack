#!/usr/bin/env python3
"""
Unsubscribe Request Processor
Appends target email to unsubscribed.txt and logs action.
"""
import os
import sys
import argparse

UNSUBSCRIBED_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "unsubscribed.txt"))

def add_unsubscribe(email):
    clean_email = email.strip().lower()
    if not clean_email:
        print("Error: Invalid email provided.")
        return False

    existing = set()
    if os.path.exists(UNSUBSCRIBED_PATH):
        with open(UNSUBSCRIBED_PATH, "r", encoding="utf-8") as f:
            existing = set(line.strip().lower() for line in f if line.strip())

    if clean_email in existing:
        print(f"Address {clean_email} is already unsubscribed.")
        return True

    with open(UNSUBSCRIBED_PATH, "a", encoding="utf-8") as f:
        f.write(f"{clean_email}\n")

    print(f"Successfully unsubscribed {clean_email} and saved to {UNSUBSCRIBED_PATH}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unsubscribe email address")
    parser.add_argument("email", type=str, help="Email address to unsubscribe")
    args = parser.parse_args()
    add_unsubscribe(args.email)
