"""Workspace ACL helpers."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.db.models import WorkspaceRole
from app.security.auth import AuthContext

_ROLE_RANK = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.EDITOR: 2,
    WorkspaceRole.OWNER: 3,
}


def require_workspace_role(
    auth: AuthContext,
    workspace_id: uuid.UUID,
    minimum: WorkspaceRole,
) -> WorkspaceRole:
    role = auth.role_for(workspace_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace access denied",
        )
    if _ROLE_RANK[role] < _ROLE_RANK[minimum]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {minimum.value} role",
        )
    return role
