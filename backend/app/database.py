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
    }).execute()
    return response.data[0]["id"]


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
