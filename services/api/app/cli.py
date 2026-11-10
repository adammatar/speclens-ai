"""SpecLens management CLI (bootstrap + API keys).

Examples:
  python -m app.cli bootstrap-local
  python -m app.cli keys create --email owner@example.com --name prod
  python -m app.cli keys list
  python -m app.cli keys disable --id <uuid>
  python -m app.cli keys rotate --id <uuid>
"""

from __future__ import annotations

import argparse
import sys
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security_startup import SecurityStartupError, assert_safe_for_hosted
from app.db.models import WorkspaceRole
from app.db.session import SessionLocal
from app.security.keys import (
    LOCAL_BOOTSTRAP_KEY,
    bootstrap_local,
    create_api_key,
    disable_api_key,
    ensure_membership,
    ensure_user,
    ensure_workspace,
    generate_api_key,
    list_api_keys,
    rotate_api_key,
)


def _session() -> Session:
    return SessionLocal()


def cmd_bootstrap_local(_: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.speclens_deployment_mode == "hosted" or settings.speclens_env == "production":
        print(
            "Refusing bootstrap-local in hosted/production. "
            "Create a high-entropy key with: python -m app.cli keys create",
            file=sys.stderr,
        )
        return 2
    session = _session()
    try:
        created = bootstrap_local(session)
    finally:
        session.close()
    print("Local bootstrap ready.")
    print(f"  user: {created.email}")
    print(f"  key_id: {created.key_id}")
    print(f"  key_prefix: {created.key_prefix}")
    print(f"  plaintext (store securely; shown once): {created.plaintext}")
    return 0


def cmd_keys_create(args: argparse.Namespace) -> int:
    settings = get_settings()
    session = _session()
    try:
        if settings.speclens_deployment_mode == "hosted" or settings.speclens_env == "production":
            # Soft check: still allow create, but refuse using the public local key.
            pass
        ensure_workspace(session)
        user = ensure_user(
            session,
            email=args.email,
            display_name=args.display_name or args.email.split("@", 1)[0],
        )
        ensure_membership(
            session,
            workspace_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
            user_id=user.id,
            role=WorkspaceRole.OWNER,
        )
        raw = generate_api_key()
        if raw == LOCAL_BOOTSTRAP_KEY:
            print("Refusing to create the known local bootstrap key.", file=sys.stderr)
            return 2
        created = create_api_key(session, user=user, name=args.name, plaintext=raw)
        session.commit()
    finally:
        session.close()
    print("API key created. Plaintext is shown once; only the hash is stored.")
    print(f"  key_id: {created.key_id}")
    print(f"  email: {created.email}")
    print(f"  name: {created.name}")
    print(f"  key_prefix: {created.key_prefix}")
    print(f"  plaintext: {created.plaintext}")
    return 0


def cmd_keys_list(_: argparse.Namespace) -> int:
    session = _session()
    try:
        rows = list_api_keys(session)
    finally:
        session.close()
    if not rows:
        print("No API keys.")
        return 0
    for row in rows:
        email = row.user.email if row.user else "?"
        print(
            f"{row.id}  active={row.is_active}  prefix={row.key_prefix}  "
            f"name={row.name}  email={email}  created={row.created_at}"
        )
    return 0


def cmd_keys_disable(args: argparse.Namespace) -> int:
    session = _session()
    try:
        key = disable_api_key(session, uuid.UUID(args.id))
        session.commit()
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        session.close()
    print(f"Disabled key {key.id} (prefix={key.key_prefix})")
    return 0


def cmd_keys_rotate(args: argparse.Namespace) -> int:
    session = _session()
    try:
        created = rotate_api_key(session, uuid.UUID(args.id))
        session.commit()
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        session.close()
    print("Rotated. Old key is inactive. New plaintext shown once:")
    print(f"  key_id: {created.key_id}")
    print(f"  key_prefix: {created.key_prefix}")
    print(f"  plaintext: {created.plaintext}")
    return 0


def cmd_check_startup(_: argparse.Namespace) -> int:
    settings = get_settings()
    session = _session()
    try:
        assert_safe_for_hosted(settings, session)
    except SecurityStartupError as exc:
        print(f"Startup check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
    print("Startup security check passed.")
    return 0


def cmd_retention_sweep(args: argparse.Namespace) -> int:
    from app.retention.service import run_retention_sweep

    settings = get_settings()
    dry_run = not args.execute
    if not dry_run and not settings.retention_sweep_enabled and not args.force:
        print(
            "Refusing destructive retention sweep: set RETENTION_SWEEP_ENABLED=true "
            "or pass --force (hosted ops only).",
            file=sys.stderr,
        )
        return 2
    session = _session()
    try:
        result = run_retention_sweep(session, dry_run=dry_run, settings=settings)
    finally:
        session.close()
    print(
        f"Retention sweep dry_run={result.dry_run} days={result.retention_days} "
        f"candidates={len(result.candidates)} deleted={len(result.deleted_ids)} "
        f"errors={len(result.errors)}"
    )
    for candidate in result.candidates[:20]:
        print(
            f"  {candidate.document_id} workspace={candidate.workspace_id} "
            f"created={candidate.created_at.isoformat()} versions={candidate.version_count}"
        )
    for err in result.errors:
        print(f"  error: {err}", file=sys.stderr)
    return 1 if result.errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_boot = sub.add_parser("bootstrap-local", help="Seed local/CI bootstrap user+key")
    p_boot.set_defaults(func=cmd_bootstrap_local)

    p_check = sub.add_parser("check-startup", help="Run hosted/production security checks")
    p_check.set_defaults(func=cmd_check_startup)

    p_ret = sub.add_parser("retention-sweep", help="Delete documents older than RETENTION_DAYS")
    p_ret.add_argument(
        "--execute",
        action="store_true",
        help="Perform deletes (default is dry-run)",
    )
    p_ret.add_argument(
        "--force",
        action="store_true",
        help="Allow deletes even when RETENTION_SWEEP_ENABLED is false",
    )
    p_ret.set_defaults(func=cmd_retention_sweep)

    keys = sub.add_parser("keys", help="API key management")
    keys_sub = keys.add_subparsers(dest="keys_command", required=True)

    p_create = keys_sub.add_parser("create", help="Create high-entropy API key")
    p_create.add_argument("--email", required=True)
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--display-name", default=None)
    p_create.set_defaults(func=cmd_keys_create)

    p_list = keys_sub.add_parser("list", help="List key metadata (no secrets)")
    p_list.set_defaults(func=cmd_keys_list)

    p_disable = keys_sub.add_parser("disable", help="Disable a key by id")
    p_disable.add_argument("--id", required=True)
    p_disable.set_defaults(func=cmd_keys_disable)

    p_rotate = keys_sub.add_parser("rotate", help="Disable old key and create a new one")
    p_rotate.add_argument("--id", required=True)
    p_rotate.set_defaults(func=cmd_keys_rotate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
