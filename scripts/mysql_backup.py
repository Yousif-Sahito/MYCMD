"""Create or restore an encrypted-at-rest MySQL logical backup with explicit confirmation."""

import argparse
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def mysql_cli_args(database_url: str) -> tuple[list[str], str]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise RuntimeError("MYCMD_MYSQL_BACKUP_URL must be a MySQL URL")
    if not parsed.hostname or not parsed.username or not parsed.password:
        raise RuntimeError("MySQL backup URL must include host, user and password")
    args = [
        f"--host={parsed.hostname}",
        f"--port={parsed.port or 3306}",
        f"--user={parsed.username}",
        parsed.path.lstrip("/"),
    ]
    return args, parsed.password


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="action", required=True)
    create = subcommands.add_parser("create")
    create.add_argument("output", type=Path)
    create.add_argument("--unencrypted", action="store_true")
    create.add_argument("--password-env", default="MYCMD_MYSQL_BACKUP_PASSWORD")
    restore = subcommands.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--confirm", action="store_true")
    restore.add_argument("--password-env", default="MYCMD_MYSQL_BACKUP_PASSWORD")
    args = parser.parse_args()
    database_url = os.getenv("MYCMD_MYSQL_BACKUP_URL", "")
    cli_args, password = mysql_cli_args(database_url)
    env = os.environ.copy()
    env["MYSQL_PWD"] = password
    if args.action == "create":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            dir=args.output.parent,
            prefix=".mycmd-mysql-",
            suffix=".sql",
        )
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            with temporary.open("wb") as output:
                subprocess.run(
                    ["mysqldump", *cli_args],
                    stdout=output,
                    env=env,
                    check=True,
                )
            if args.unencrypted:
                temporary.replace(args.output)
            else:
                password_value = os.getenv(args.password_env, "")
                if not password_value:
                    raise RuntimeError(
                        f"Set {args.password_env} before creating an encrypted backup"
                    )
                salt = os.urandom(16)
                plaintext = temporary.read_bytes()
                ciphertext = Fernet(derive_key(password_value, salt)).encrypt(plaintext)
                envelope = {
                    "format": "mycmd-mysql-backup",
                    "algorithm": "Fernet-PBKDF2-SHA256",
                    "kdf_iterations": 600_000,
                    "salt": base64.b64encode(salt).decode("ascii"),
                    "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
                }
                args.output.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
                os.chmod(args.output, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        os.chmod(args.output, 0o600)
        print(f"Created MySQL backup: {args.output}")
        return 0
    if not args.confirm:
        raise RuntimeError("Restore requires --confirm")
    if not args.backup.is_file():
        raise RuntimeError("Backup file does not exist")
    fd, temporary_name = tempfile.mkstemp(
        dir=args.backup.parent,
        prefix=".mycmd-mysql-restore-",
        suffix=".sql",
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        try:
            envelope = json.loads(args.backup.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            envelope = None
        if envelope is not None:
            password_value = os.getenv(args.password_env, "")
            if not password_value:
                raise RuntimeError(f"Set {args.password_env} before restoring an encrypted backup")
            try:
                salt = base64.b64decode(envelope["salt"], validate=True)
                ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
                plaintext = Fernet(derive_key(password_value, salt)).decrypt(ciphertext)
            except (KeyError, ValueError, InvalidToken) as exc:
                raise RuntimeError("Wrong MySQL backup key or corrupted ciphertext") from exc
            temporary.write_bytes(plaintext)
        else:
            temporary.write_bytes(args.backup.read_bytes())
        with temporary.open("rb") as backup:
            subprocess.run(
                ["mysql", *cli_args],
                stdin=backup,
                env=env,
                check=True,
            )
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Restored MySQL backup: {args.backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
