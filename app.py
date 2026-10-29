from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from database import (
    DATABASE_PATH,
    TASK_CATEGORIES,
    TASK_PRIORITIES,
    TASK_STATUSES,
    add_task,
    authenticate,
    create_user,
    delete_task,
    get_tasks,
    init_db,
    update_task,
)


st.set_page_config(
    page_title="Personal Task Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db(DATABASE_PATH)

st.markdown(
    """
    <style>
    .stApp { background: #f7f8fc; }
    [data-testid="stSidebar"] { background: #111827; }
    [data-testid="stSidebar"] * { color: #f9fafb; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e8eaf0; border-radius: 12px;
        padding: 16px 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_authentication() -> None:
    st.title("📚 Personal Task Manager")
    st.write("A calmer way to keep assignments, exams, and deadlines in view.")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Log in", type="primary", use_container_width=True
            )
        if submitted:
            user = authenticate(username, password, DATABASE_PATH)
            if user is None:
                st.error("Incorrect username or password.")
            else:
                st.session_state["user"] = user
                st.rerun()

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Choose a username", key="register_username")
            password = st.text_input(
                "Choose a password", type="password", key="register_password"
            )
            confirm_password = st.text_input(
                "Confirm password", type="password", key="confirm_password"
            )
            submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )
        if submitted:
            if password != confirm_password:
                st.error("The passwords do not match.")
            else:
                try:
                    user_id = create_user(username, password, DATABASE_PATH)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state["user"] = {
                        "id": user_id,
                        "username": username.strip().lower(),
                    }
                    st.rerun()

    st.caption("Demo login: admin / admin123")


def render_dashboard(user_id: int) -> None:
    tasks = get_tasks(user_id, DATABASE_PATH)
    today = date.today()
    completed = [task for task in tasks if task["status"] == "Completed"]
    pending = [task for task in tasks if task["status"] == "Pending"]
    in_progress = [task for task in tasks if task["status"] == "In Progress"]
    overdue = [
        task
        for task in tasks
        if task["status"] != "Completed"
        and date.fromisoformat(str(task["due_date"])) < today
    ]
    upcoming = [
        task
        for task in tasks
        if task["status"] != "Completed"
        and today
        <= date.fromisoformat(str(task["due_date"]))
        <= today + timedelta(days=7)
    ]

    st.title("Your study dashboard")
    st.caption(f"{today.strftime('%A, %B %d')} · One step at a time.")
    metrics = st.columns(5)
    metrics[0].metric("All tasks", len(tasks))
    metrics[1].metric("Pending", len(pending))
    metrics[2].metric("In progress", len(in_progress))
    metrics[3].metric("Completed", len(completed))
    metrics[4].metric("Overdue", len(overdue), delta_color="inverse")

    chart_column, deadlines_column = st.columns([1, 1])
    with chart_column:
        st.subheader("Tasks by status")
        st.bar_chart(
            {
                "Pending": len(pending),
                "In Progress": len(in_progress),
                "Completed": len(completed),
            },
            color=["#6366f1"],
        )
    with deadlines_column:
        st.subheader("Coming up")
        if upcoming:
            for task in upcoming:
                st.write(
                    f"**{task['name']}** · {task['category']} · "
                    f"{task['priority']} · {task['due_date']}"
                )
        else:
            st.info("No deadlines in the next 7 days.")

    st.subheader("Overdue tasks")
    if overdue:
        for task in overdue:
            st.error(f"{task['name']} · Due {task['due_date']}")
    else:
        st.success("You’re all caught up on overdue tasks.")


def render_add_task(user_id: int) -> None:
    st.title("Add a task")
    st.caption("Capture what needs to get done and when.")
    with st.form("add_task_form", clear_on_submit=True):
        name = st.text_input("Task name", max_chars=120)
        category = st.selectbox("Category", TASK_CATEGORIES)
        priority = st.selectbox("Priority", ("Medium", "High", "Low"))
        due_date = st.date_input("Due date", value=date.today())
        status = st.selectbox("Status", TASK_STATUSES)
        submitted = st.form_submit_button(
            "Save task", type="primary", use_container_width=True
        )
    if submitted:
        try:
            add_task(user_id, name, category, priority, due_date, status, DATABASE_PATH)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Task added.")
            st.rerun()


def render_task_editor(user_id: int, task: dict[str, object]) -> None:
    task_id = int(task["id"])
    due_date = date.fromisoformat(str(task["due_date"]))
    is_overdue = task["status"] != "Completed" and due_date < date.today()
    label = f"{'🔴 Overdue · ' if is_overdue else ''}{task['name']} · {due_date}"

    with st.expander(label):
        with st.form(f"edit_task_{task_id}"):
            name = st.text_input(
                "Task name",
                value=str(task["name"]),
                max_chars=120,
                key=f"name_{task_id}",
            )
            category = st.selectbox(
                "Category",
                TASK_CATEGORIES,
                index=TASK_CATEGORIES.index(str(task["category"])),
                key=f"category_{task_id}",
            )
            priority = st.selectbox(
                "Priority",
                TASK_PRIORITIES,
                index=TASK_PRIORITIES.index(str(task["priority"])),
                key=f"priority_{task_id}",
            )
            due_date = st.date_input(
                "Due date", value=due_date, key=f"due_date_{task_id}"
            )
            status = st.selectbox(
                "Status",
                TASK_STATUSES,
                index=TASK_STATUSES.index(str(task["status"])),
                key=f"status_{task_id}",
            )
            submitted = st.form_submit_button("Save changes", type="primary")
        if submitted:
            try:
                update_task(
                    user_id,
                    task_id,
                    name,
                    category,
                    priority,
                    due_date,
                    status,
                    DATABASE_PATH,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Task updated.")
                st.rerun()

        action_columns = st.columns(2)
        if task["status"] == "Completed":
            if action_columns[0].button("Reopen task", key=f"reopen_{task_id}"):
                update_task(
                    user_id,
                    task_id,
                    str(task["name"]),
                    str(task["category"]),
                    str(task["priority"]),
                    str(task["due_date"]),
                    "Pending",
                    DATABASE_PATH,
                )
                st.rerun()
        elif action_columns[0].button("Mark complete", key=f"complete_{task_id}"):
            update_task(
                user_id,
                task_id,
                str(task["name"]),
                str(task["category"]),
                str(task["priority"]),
                str(task["due_date"]),
                "Completed",
                DATABASE_PATH,
            )
            st.rerun()
        if action_columns[1].button("Delete task", key=f"delete_{task_id}"):
            delete_task(user_id, task_id, DATABASE_PATH)
            st.rerun()


def render_tasks(user_id: int) -> None:
    st.title("Your tasks")
    tasks = get_tasks(user_id, DATABASE_PATH)
    if not tasks:
        st.info("No tasks yet. Add your first one from the sidebar.")
        return

    filters = st.columns(4)
    status_filter = filters[0].selectbox(
        "Status", ["All", *TASK_STATUSES], key="filter_status"
    )
    priority_filter = filters[1].selectbox(
        "Priority", ["All", *TASK_PRIORITIES], key="filter_priority"
    )
    category_filter = filters[2].selectbox(
        "Category", ["All", *TASK_CATEGORIES], key="filter_category"
    )
    sort_order = filters[3].selectbox(
        "Sort by",
        [
            "Deadline (soonest)",
            "Deadline (latest)",
            "Priority (high to low)",
            "Status",
            "Category (A–Z)",
            "Name (A–Z)",
        ],
    )

    filtered_tasks = [
        task
        for task in tasks
        if (status_filter == "All" or task["status"] == status_filter)
        and (priority_filter == "All" or task["priority"] == priority_filter)
        and (category_filter == "All" or task["category"] == category_filter)
    ]
    if sort_order == "Deadline (latest)":
        filtered_tasks.sort(key=lambda task: str(task["due_date"]), reverse=True)
    elif sort_order == "Priority (high to low)":
        priority_order = {value: index for index, value in enumerate(TASK_PRIORITIES)}
        filtered_tasks.sort(key=lambda task: priority_order[str(task["priority"])])
    elif sort_order == "Status":
        status_order = {value: index for index, value in enumerate(TASK_STATUSES)}
        filtered_tasks.sort(key=lambda task: status_order[str(task["status"])])
    elif sort_order == "Category (A–Z)":
        filtered_tasks.sort(key=lambda task: str(task["category"]).casefold())
    elif sort_order == "Name (A–Z)":
        filtered_tasks.sort(key=lambda task: str(task["name"]).casefold())

    st.caption(f"Showing {len(filtered_tasks)} of {len(tasks)} tasks")
    st.dataframe(
        [
            {
                "Task": task["name"],
                "Category": task["category"],
                "Priority": task["priority"],
                "Due date": task["due_date"],
                "Status": task["status"],
            }
            for task in filtered_tasks
        ],
        use_container_width=True,
        hide_index=True,
    )
    for task in filtered_tasks:
        render_task_editor(user_id, task)


user = st.session_state.get("user")
if user is None:
    render_authentication()
else:
    with st.sidebar:
        st.title("📚 Study planner")
        st.caption(f"Signed in as **{user['username']}**")
        page = st.radio("Navigate", ["Dashboard", "Add Task", "View Tasks"])
        if st.button("Log out", use_container_width=True):
            del st.session_state["user"]
            st.rerun()

    user_id = int(user["id"])
    if page == "Dashboard":
        render_dashboard(user_id)
    elif page == "Add Task":
        render_add_task(user_id)
    else:
        render_tasks(user_id)
