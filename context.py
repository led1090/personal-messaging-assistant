from ai_agents import chat_agent, food_analysis_agent
from database.repository import (
    get_or_create_user,
    update_user_goal,
    get_last_meal,
    update_meal,
    delete_meal,
    get_user_today_macros,
    log_meal,
    get_user_meals_today,
)


def build_context_variables(phone_number: str, media_id: str = None) -> dict:
    """Build the context_variables dict with DB callbacks and agent references.

    This bridges the application layer (database, config) and the ai-agents
    package. All DB operations are passed as callable values so agents have
    zero knowledge of the database layer.
    """
    ctx = {
        # Identity
        "phone_number": phone_number,
        # DB callbacks
        "get_or_create_user": get_or_create_user,
        "update_user_goal": update_user_goal,
        "get_last_meal": get_last_meal,
        "update_meal": update_meal,
        "delete_meal": delete_meal,
        "get_user_today_macros": get_user_today_macros,
        "log_meal": log_meal,
        "get_user_meals_today": get_user_meals_today,
        # Agent cross-references (for handoffs)
        "chat_agent": chat_agent,
        "food_analysis_agent": food_analysis_agent,
    }
    if media_id:
        ctx["media_id"] = media_id
    return ctx
