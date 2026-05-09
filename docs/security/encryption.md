# Encryption

## Encryption Stack

| Layer | Algorithm |
|-------|-----------|
| Cipher | Fernet (AES-128-CBC + HMAC-SHA256) |
| Key Derivation | PBKDF2-HMAC-SHA256 |
| Iterations | 1,000,000 (new), 480,000 (legacy fallback) |
| Salt | Random 16 bytes, stored in `~/.slink/salt` |

## What Is Encrypted vs. Plaintext

| Data | State |
|------|-------|
| Host names & aliases | Plaintext (in `.show_direct`) |
| IP, port, username | Encrypted |
| SSH passwords | Encrypted |
| Private key paths | Encrypted |
| Jump host chains | Encrypted |

The plaintext `.show_direct` enables shell completion and fast name listing without decrypting the full database.

## Password Rotation

`sli passwd` performs:

1. Decrypts all hosts with the old password (fallback to 480k iterations if needed).
2. Generates a new random salt.
3. Re-encrypts everything with the new password at 1M iterations.
4. Atomically replaces the salt file.

## Agent Temporary Password

`sli agent-pass --ttl 300` generates a temporary read-only password valid for 300 seconds, enabling automated workflows without exposing the master password.
