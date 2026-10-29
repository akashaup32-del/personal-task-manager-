from datetime import date, timedelta

import pytest

from database import (
    add_task,
    authenticate,
    create_user,
    delete_task,
    get_tasks,
    init_db,
    update_task,
)


@pytest.fixture
def database_path(tmp_path):
    path = tmp_path / "test_tasks.db"
    init_db(path)
    return path


def test_seeded_account_authenticates(database_path):
    user = authenticate("admin", "admin123", database_path)

    assert user is not None
    assert user["username"] == "admin"
    assert authenticate("admin", "wrong-password", database_path) is None


def test_registration_normalizes_username_and_rejects_duplicate(database_path):
    user_id = create_user("NewStudent", "password123", database_path)

    assert authenticate("newstudent", "password123", database_path)["id"] == user_id
    with pytest.raises(ValueError, match="already taken"):
        create_user("NEWSTUDENT", "different123", database_path)


def test_task_crud_and_user_isolation(database_path):
    first_user = authenticate("admin", "admin123", database_path)["id"]
    second_user = create_user("student2", "password123", database_path)

    task_id = add_task(
        first_user,
        "Submit report",
        "Assignment",
        "High",
        date.today() + timedelta(days=2),
        db_path=database_path,
    )
    assert len(get_tasks(first_user, database_path)) == 1
    assert get_tasks(second_user, database_path) == []

    update_task(
        first_user,
        task_id,
        "Submit final report",
        "Project",
        "Medium",
        date.today() + timedelta(days=3),
        "In Progress",
        database_path,
    )
    assert get_tasks(first_user, database_path)[0]["name"] == "Submit final report"

    with pytest.raises(LookupError):
        update_task(
            second_user,
            task_id,
            "Another user's task",
            "Project",
            "Low",
            date.today(),
            "Completed",
            database_path,
        )
    with pytest.raises(LookupError):
        delete_task(second_user, task_id, database_path)
    assert get_tasks(first_user, database_path)[0]["name"] == "Submit final report"

    delete_task(first_user, task_id, database_path)
    assert get_tasks(first_user, database_path) == []


@pytest.mark.parametrize(
    ("name", "category", "priority", "due_date", "status"),
    [
        (" ", "Assignment", "High", "2026-10-30", "Pending"),
        ("x" * 121, "Assignment", "High", "2026-10-30", "Pending"),
        ("Task", "Invalid", "High", "2026-10-30", "Pending"),
        ("Task", "Assignment", "Urgent", "2026-10-30", "Pending"),
        ("Task", "Assignment", "High", "not-a-date", "Pending"),
        ("Task", "Assignment", "High", "2026-02-30", "Pending"),
        ("Task", "Assignment", "High", "2026-10-30", "Blocked"),
    ],
)
def test_invalid_tasks_are_rejected(
    database_path, name, category, priority, due_date, status
):
    user_id = authenticate("admin", "admin123", database_path)["id"]

    with pytest.raises(ValueError):
        add_task(user_id, name, category, priority, due_date, status, database_path)


def test_init_db_is_idempotent(database_path):
    init_db(database_path)

    assert authenticate("admin", "admin123", database_path) is not None
