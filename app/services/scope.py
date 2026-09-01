from __future__ import annotations

from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Asset, ClientUnit, Role, User, UserClientAssignment, UserClientUnitAssignment

CLIENT_ROLES = {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}


def assigned_client_ids(db: Session, user: User) -> set[int]:
    if user.role in CLIENT_ROLES:
        return {user.client_id} if user.client_id else set()
    if user.role == Role.SYSTEM_ADMIN.value:
        return set()
    ids = db.scalars(
        select(UserClientAssignment.client_id).where(
            UserClientAssignment.user_id == user.id,
            UserClientAssignment.active.is_(True),
        )
    ).all()
    return set(ids)


def can_access_client(db: Session, user: User, client_id: int) -> bool:
    if user.role == Role.SYSTEM_ADMIN.value:
        return True
    if user.role in CLIENT_ROLES:
        return user.client_id == client_id
    assigned = assigned_client_ids(db, user)
    if user.role in {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}:
        if user.client_id:
            return user.client_id == client_id
        return client_id in assigned
    return not assigned or client_id in assigned


def can_access_site(user: User, site_id: int) -> bool:
    return user.role == Role.SYSTEM_ADMIN.value or user.site_id is None or user.site_id == site_id


def _unit_tree(db: Session, client_id: int) -> tuple[dict[int, ClientUnit], dict[int | None, list[int]]]:
    units = db.scalars(
        select(ClientUnit).where(ClientUnit.client_id == client_id, ClientUnit.active.is_(True))
    ).all()
    by_id = {u.id: u for u in units}
    children: dict[int | None, list[int]] = defaultdict(list)
    for u in units:
        children[u.parent_id].append(u.id)
    return by_id, children


def descendant_unit_ids(db: Session, client_id: int, root_ids: set[int]) -> set[int]:
    """Return each assigned unit plus every active descendant for the same client."""
    by_id, children = _unit_tree(db, client_id)
    valid_roots = {rid for rid in root_ids if rid in by_id}
    result: set[int] = set()
    queue = deque(valid_roots)
    while queue:
        uid = queue.popleft()
        if uid in result:
            continue
        result.add(uid)
        queue.extend(children.get(uid, []))
    return result


def assigned_client_unit_ids(db: Session, user: User) -> set[int]:
    return set(
        db.scalars(
            select(UserClientUnitAssignment.client_unit_id).where(
                UserClientUnitAssignment.user_id == user.id,
                UserClientUnitAssignment.active.is_(True),
            )
        ).all()
    )


def allowed_client_unit_ids(db: Session, user: User, client_id: int) -> set[int] | None:
    """
    None means the user has company-wide visibility for this client.
    A set means visibility is limited to those units and their descendants.
    """
    if user.role == Role.SYSTEM_ADMIN.value:
        return None
    if not can_access_client(db, user, client_id):
        return set()
    assigned = assigned_client_unit_ids(db, user)
    if not assigned:
        return None
    roots = set(
        db.scalars(
            select(ClientUnit.id).where(ClientUnit.id.in_(assigned), ClientUnit.client_id == client_id)
        ).all()
    )
    if not roots:
        return set()
    return descendant_unit_ids(db, client_id, roots)


def can_access_asset(db: Session, user: User, asset: Asset) -> bool:
    if not can_access_client(db, user, asset.client_id):
        return False
    allowed = allowed_client_unit_ids(db, user, asset.client_id)
    if allowed is None:
        return True
    if asset.client_unit_id is None:
        return False
    return asset.client_unit_id in allowed


def client_scope_labels(db: Session, user: User) -> list[str]:
    if user.role not in CLIENT_ROLES or not user.client_id:
        return []
    assigned = assigned_client_unit_ids(db, user)
    if not assigned:
        return ["All company units"]
    units = db.scalars(select(ClientUnit).where(ClientUnit.id.in_(assigned)).order_by(ClientUnit.name)).all()
    return [f"{u.unit_type.title()}: {u.name}" for u in units]
