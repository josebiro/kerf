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
