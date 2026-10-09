"""SQLite accounts, invitations and revocable cookie sessions for the hosted lab."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from fastapi import HTTPException


def password_hash(password: str, salt: str | None = None) -> str:
    if not 12 <= len(password) <= 128:
        raise ValueError("密码需要 12～128 个字符")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 600_000
    )
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def password_matches(password: str, encoded: str) -> bool:
    if not 12 <= len(password) <= 128:
        return False
    _, salt, _ = encoded.split("$")
    return hmac.compare_digest(password_hash(password, salt), encoded)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(row) -> dict:
    user = {
        key: row[key]
        for key in (
            "id",
            "username",
            "display_name",
            "role",
            "enabled",
            "must_change_password",
            "created_at",
        )
    }
    user["enabled"] = bool(user["enabled"])
    user["must_change_password"] = bool(user["must_change_password"])
    return user


class Accounts:
    def __init__(self, root: Path, *, max_users=200, session_hours=12):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = root / "accounts.sqlite3"
        self.max_users, self.session_seconds = max_users, session_hours * 3600
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL, password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
                    enabled INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    expires REAL NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS session_user ON sessions(user_id);
                CREATE TABLE IF NOT EXISTS invitations (
                    token TEXT PRIMARY KEY, remaining INTEGER NOT NULL,
                    expires REAL NOT NULL, created_by TEXT NOT NULL REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, at REAL NOT NULL, actor TEXT,
                    action TEXT NOT NULL, target TEXT NOT NULL
                );
            """)
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def audit(db, actor, action, target):
        db.execute(
            "INSERT INTO audit(at,actor,action,target) VALUES(?,?,?,?)",
            (time.time(), actor, action, target),
        )
        db.execute("DELETE FROM audit WHERE id < (SELECT MAX(id)-10000 FROM audit)")

    def throttle(self, key: str, limit=10, seconds=900):
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM attempts WHERE expires < ?", (now,))
            row = db.execute(
                "SELECT count FROM attempts WHERE key=?", (key,)
            ).fetchone()
            if row and row["count"] >= limit:
                raise HTTPException(
                    429,
                    "操作过于频繁，请稍后重试",
                    headers={"Retry-After": str(seconds)},
                )
            # Fixed windows; bounded by expiry and the global request limiter.
            db.execute(
                "INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1",
                (key, now + seconds),
            )

    def create(
        self,
        username,
        password,
        display_name="",
        *,
        role="student",
        actor=None,
        invitation=None,
        must_change=False,
    ):
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,31}", username):
            raise ValueError("账号须为 3～32 位字母、数字、点、下划线或短横线")
        display_name = display_name.strip() or username
        if len(display_name) > 60 or role not in {"student", "admin"}:
            raise ValueError("姓名或角色无效")
        encoded = password_hash(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= self.max_users:
                raise HTTPException(409, "账号数量已达上限，请联系管理员")
            if invitation is not None:
                updated = db.execute(
                    "UPDATE invitations SET remaining=remaining-1 WHERE token=? AND remaining>0 AND expires>?",
                    (token_hash(invitation), time.time()),
                )
                if not updated.rowcount:
                    raise ValueError("邀请码无效、已过期或已用完")
            identifier = uuid.uuid4().hex
            try:
                db.execute(
                    "INSERT INTO users VALUES(?,?,?,?,?,1,?,?)",
                    (
                        identifier,
                        username,
                        display_name,
                        encoded,
                        role,
                        int(must_change),
                        time.time(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(409, "账号已存在") from error
            self.audit(db, actor, "create_user", identifier)
            return public_user(
                db.execute("SELECT * FROM users WHERE id=?", (identifier,)).fetchone()
            )

    def login(self, username: str, password: str):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM users WHERE username=?", (username.strip().lower(),)
            ).fetchone()
        valid = password_matches(password, row["password"] if row else self.dummy_hash)
        if not row or not valid or not row["enabled"]:
            raise HTTPException(401, "账号或密码错误，或账号已停用")
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Recheck after password derivation: a concurrent reset/disable must win.
            current = db.execute(
                "SELECT * FROM users WHERE id=?", (row["id"],)
            ).fetchone()
            if not current["enabled"] or current["password"] != row["password"]:
                raise HTTPException(401, "账号状态已变化，请重新登录")
            db.execute("DELETE FROM sessions WHERE expires<?", (now,))
            db.execute(
                "DELETE FROM sessions WHERE user_id=? AND token NOT IN "
                "(SELECT token FROM sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 4)",
                (row["id"], row["id"]),
            )
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (token_hash(token), row["id"], now + self.session_seconds, now),
            )
            self.audit(db, row["id"], "login", row["id"])
        return token, public_user(current)

    def authenticate(self, token: str | None):
        if not token or len(token) > 128:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id "
                "WHERE s.token=? AND s.expires>? AND u.enabled=1",
                (token_hash(token), time.time()),
            ).fetchone()
            return public_user(row) if row else None

    def logout(self, token: str):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token=?", (token_hash(token),))

    def change_password(self, identifier, old_password, new_password):
        encoded = password_hash(new_password)
        with self.connect() as db:
            row = db.execute(
                "SELECT password FROM users WHERE id=?", (identifier,)
            ).fetchone()
        if not row or not password_matches(old_password, row["password"]):
            raise HTTPException(400, "原密码不正确")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE users SET password=?,must_change_password=0 WHERE id=? AND password=?",
                (encoded, identifier, row["password"]),
            )
            if not result.rowcount:
                raise HTTPException(409, "密码已被修改，请重新登录")
            db.execute("DELETE FROM sessions WHERE user_id=?", (identifier,))
            self.audit(db, identifier, "change_password", identifier)

    def update(self, identifier, *, actor, enabled=None, reset_password=None):
        encoded = password_hash(reset_password) if reset_password else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute(
                "SELECT * FROM users WHERE id=?", (identifier,)
            ).fetchone()
            if not user:
                raise HTTPException(404, "账号不存在")
            if enabled is False and user["role"] == "admin":
                count = db.execute(
                    "SELECT COUNT(*) FROM users WHERE role='admin' AND enabled=1"
                ).fetchone()[0]
                if identifier == actor or (user["enabled"] and count <= 1):
                    raise HTTPException(409, "不能停用自己或最后一个管理员")
            if enabled is not None:
                db.execute(
                    "UPDATE users SET enabled=? WHERE id=?", (int(enabled), identifier)
                )
            if encoded:
                db.execute(
                    "UPDATE users SET password=?,must_change_password=1 WHERE id=?",
                    (encoded, identifier),
                )
            if enabled is False or encoded:
                db.execute("DELETE FROM sessions WHERE user_id=?", (identifier,))
            self.audit(
                db, actor, "reset_password" if encoded else "set_enabled", identifier
            )
            return public_user(
                db.execute("SELECT * FROM users WHERE id=?", (identifier,)).fetchone()
            )

    def invite(self, actor, uses=1, days=7):
        if not 1 <= uses <= 200 or not 1 <= days <= 30:
            raise ValueError("邀请码允许 1～200 人使用，有效期 1～30 天")
        token = secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute(
                "DELETE FROM invitations WHERE expires<? OR remaining=0", (time.time(),)
            )
            db.execute(
                "INSERT INTO invitations VALUES(?,?,?,?)",
                (token_hash(token), uses, time.time() + days * 86400, actor),
            )
            self.audit(db, actor, "create_invitation", str(uses))
        return token

    def users(self):
        with self.connect() as db:
            return [
                public_user(row)
                for row in db.execute("SELECT * FROM users ORDER BY created_at")
            ]

    def invitations(self):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT token AS id,remaining,expires FROM invitations WHERE expires>? AND remaining>0 ORDER BY expires",
                    (time.time(),),
                )
            ]

    def revoke_invitation(self, identifier, actor):
        with self.connect() as db:
            db.execute("DELETE FROM invitations WHERE token=?", (identifier,))
            self.audit(db, actor, "revoke_invitation", identifier)

    def may_run(self, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT enabled,must_change_password FROM users WHERE id=?",
                (identifier,),
            ).fetchone()
            return bool(row and row["enabled"] and not row["must_change_password"])

    def events(self):
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100")
            ]
