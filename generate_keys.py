"""
generate_keys.py — SSL Key Pair Generator for GenStack / StackGPT
-----------------------------------------------------------------
Generates a self-signed SSL certificate and private key and saves them
into the keys/ folder so that server.py can start with HTTPS enabled.

Usage:
    python generate_keys.py

Output:
    keys/privkey.pem   — RSA 4096-bit private key
    keys/fullchain.pem — Self-signed X.509 certificate

NOTE: Self-signed certificates are for LOCAL DEVELOPMENT ONLY.
      For production, replace these files with real certificates from
      Let's Encrypt (certbot) or your certificate authority.
"""

import os
import datetime
import ipaddress

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# ── Configuration ────────────────────────────────────────────────────────────
KEYS_DIR       = "keys"
KEY_FILE       = os.path.join(KEYS_DIR, "privkey.pem")
CERT_FILE      = os.path.join(KEYS_DIR, "fullchain.pem")
KEY_SIZE       = 4096          # RSA key size in bits
CERT_VALID_DAYS = 825          # ~2 years (browser limit for self-signed)

# Certificate subject fields (safe defaults for local dev)
COUNTRY        = "US"
STATE          = "Local"
LOCALITY       = "Localhost"
ORGANIZATION   = "GenStack Dev"
COMMON_NAME    = "localhost"
# ─────────────────────────────────────────────────────────────────────────────


def print_banner():
    print()
    print("=" * 60)
    print("  GenStack — SSL Key Generator")
    print("=" * 60)
    print()


def ensure_keys_dir():
    if not os.path.exists(KEYS_DIR):
        os.makedirs(KEYS_DIR)
        print(f"[+] Created directory: {KEYS_DIR}/")
    else:
        print(f"[+] Directory exists:  {KEYS_DIR}/")


def generate_private_key():
    print(f"[+] Generating RSA {KEY_SIZE}-bit private key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=KEY_SIZE,
        backend=default_backend()
    )
    return key


def save_private_key(key):
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(KEY_FILE, "wb") as f:
        f.write(key_pem)
    # Restrict permissions on Unix-like systems
    try:
        os.chmod(KEY_FILE, 0o600)
    except AttributeError:
        pass  # Windows doesn't support chmod
    print(f"[+] Private key saved:  {KEY_FILE}")


def generate_certificate(key):
    print(f"[+] Generating self-signed certificate (valid {CERT_VALID_DAYS} days)...")

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             COUNTRY),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   STATE),
        x509.NameAttribute(NameOID.LOCALITY_NAME,            LOCALITY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        ORGANIZATION),
        x509.NameAttribute(NameOID.COMMON_NAME,              COMMON_NAME),
    ])

    now = datetime.datetime.utcnow()

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CERT_VALID_DAYS))
        # Subject Alternative Names — required by modern browsers
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1")),
            ]),
            critical=False,
        )
        # Mark as a CA certificate so it can sign itself
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    return cert


def save_certificate(cert):
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    with open(CERT_FILE, "wb") as f:
        f.write(cert_pem)
    print(f"[+] Certificate saved:  {CERT_FILE}")


def check_existing_files():
    existing = []
    if os.path.exists(KEY_FILE):
        existing.append(KEY_FILE)
    if os.path.exists(CERT_FILE):
        existing.append(CERT_FILE)

    if existing:
        print("⚠️  Existing key files detected:")
        for f in existing:
            print(f"    {f}")
        answer = input("\n   Overwrite? (y/N): ").strip().lower()
        if answer != "y":
            print("\n[!] Aborted. Existing keys kept.")
            return False
        print()
    return True


def print_summary(cert):
    not_before = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before
    not_after  = cert.not_valid_after_utc  if hasattr(cert, "not_valid_after_utc")  else cert.not_valid_after

    print()
    print("=" * 60)
    print("  ✅ SSL keys generated successfully!")
    print("=" * 60)
    print()
    print(f"  Private key : {KEY_FILE}")
    print(f"  Certificate : {CERT_FILE}")
    print(f"  Valid from  : {not_before.strftime('%Y-%m-%d')}")
    print(f"  Valid until : {not_after.strftime('%Y-%m-%d')}")
    print(f"  Key size    : RSA {KEY_SIZE}-bit")
    print(f"  Common name : {COMMON_NAME}")
    print()
    print("  Next step — start the server:")
    print()
    print("    python server.py")
    print()
    print("  Then open: https://localhost:8000")
    print()
    print("  ⚠️  BROWSER WARNING (expected for self-signed certs):")
    print('     Click "Advanced" → "Proceed to localhost" to continue.')
    print()
    print("  ⚠️  PRODUCTION NOTE:")
    print("     Replace keys/privkey.pem and keys/fullchain.pem with")
    print("     real certificates from Let's Encrypt (certbot).")
    print("     See README.md for instructions.")
    print()
    print("=" * 60)
    print()


def main():
    print_banner()

    # Check if overwrite is needed
    if not check_existing_files():
        return

    ensure_keys_dir()

    # Generate key + cert
    private_key = generate_private_key()
    save_private_key(private_key)

    certificate = generate_certificate(private_key)
    save_certificate(certificate)

    print_summary(certificate)


if __name__ == "__main__":
    main()
