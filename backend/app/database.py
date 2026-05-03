"""Supabase Postgres queries for the projects table."""

from typing import Any
from app.supabase_client import get_supabase_client


def create_project(
    user_id: str,
    name: str,
    filename: str,
    solid_species: str,
    sheet_type: str,
    all_solid: bool,
    display_units: str,
    analysis_result: dict,
    file_path: str,
    thumbnail_path: str | None = None,
    optimize_result: dict | None = None,
) -> str:
    """Insert a project row and return the project ID."""
    client = get_supabase_client()
    response = client.table("projects").insert({
        "user_id": user_id,
        "name": name,
        "filename": filename,
        "solid_species": solid_species,
        "sheet_type": sheet_type,
        "all_solid": all_solid,
        "display_units": display_units,
        "analysis_result": analysis_result,
        "file_path": file_path,
        "thumbnail_path": thumbnail_path,
        "optimize_result": optimize_result,
    }).execute()
    return response.data[0]["id"]


def update_project(
    project_id: str,
    user_id: str,
    analysis_result: dict,
    solid_species: str,
    sheet_type: str,
    all_solid: bool,
    display_units: str,
    optimize_result: dict | None = None,
    thumbnail_path: str | None = None,
) -> None:
    """Update an existing project's analysis results."""
    client = get_supabase_client()
    updates: dict[str, Any] = {
        "analysis_result": analysis_result,
        "solid_species": solid_species,
        "sheet_type": sheet_type,
        "all_solid": all_solid,
        "display_units": display_units,
        "optimize_result": optimize_result,
    }
    if thumbnail_path is not None:
        updates["thumbnail_path"] = thumbnail_path
    (
        client.table("projects")
        .update(updates)
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )


def list_projects(user_id: str) -> list[dict[str, Any]]:
    """List all projects for a user, newest first."""
    client = get_supabase_client()
    response = (
        client.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_project(project_id: str, user_id: str) -> dict[str, Any] | None:
    """Get a single project by ID, only if owned by user_id."""
    client = get_supabase_client()
    response = (
        client.table("projects")
        .select("*")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def delete_project(project_id: str, user_id: str) -> None:
    """Delete a project row (ownership enforced by user_id filter)."""
    client = get_supabase_client()
    (
        client.table("projects")
        .delete()
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )


def get_user_preferences(user_id: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    response = (
        client.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def upsert_user_preferences(
    user_id: str,
    enabled_suppliers: list[str] | None = None,
    default_species: str | None = None,
    default_sheet_type: str | None = None,
    default_units: str | None = None,
) -> None:
    client = get_supabase_client()
    data: dict[str, Any] = {"user_id": user_id}
    if enabled_suppliers is not None:
        data["enabled_suppliers"] = enabled_suppliers
    if default_species is not None:
        data["default_species"] = default_species
    if default_sheet_type is not None:
        data["default_sheet_type"] = default_sheet_type
    if default_units is not None:
        data["default_units"] = default_units
    client.table("user_preferences").upsert(data, on_conflict="user_id").execute()


def get_catalog(
    product_type: str | None = None,
    search: str | None = None,
    supplier_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    client = get_supabase_client()
    query = client.table("supplier_prices").select("*, suppliers(name)")
    if product_type:
        query = query.eq("product_type", product_type)
    if supplier_ids:
        query = query.in_("supplier_id", supplier_ids)
    if search:
        query = query.ilike("species_or_name", f"%{search}%")
    query = query.order("species_or_name").order("thickness")
    response = query.execute()
    return response.data


def get_suppliers() -> list[dict[str, Any]]:
    client = get_supabase_client()
    response = client.table("suppliers").select("*").eq("active", True).execute()
    return response.data
