from datetime import date, datetime, timedelta
from database.models import get_connection


def get_or_create_user(
    phone_number: str,
    first_name: str = None,
    last_name: str = None,
    username: str = None,
    language_code: str = None,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()

    if row:
        user = dict(row)
        # Sync Telegram identity fields if they've changed
        updates = {}
        if first_name is not None and user.get("first_name") != first_name:
            updates["first_name"] = first_name
        if last_name is not None and user.get("last_name") != last_name:
            updates["last_name"] = last_name
        if username is not None and user.get("username") != username:
            updates["username"] = username
        if language_code is not None and user.get("language_code") != language_code:
            updates["language_code"] = language_code
        if first_name is not None:
            new_display = (first_name + " " + (last_name or "")).strip()
            if user.get("display_name") != new_display:
                updates["display_name"] = new_display
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [phone_number]
            conn.execute(
                f"UPDATE users SET {set_clause} WHERE phone_number = ?",
                values,
            )
            conn.commit()
            user.update(updates)
        conn.close()
        return user

    display_name = None
    if first_name:
        display_name = (first_name + " " + (last_name or "")).strip()

    cursor.execute(
        """INSERT INTO users (phone_number, first_name, last_name, username,
           language_code, display_name)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (phone_number, first_name, last_name or "", username or "",
         language_code or "en", display_name),
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user


def update_user_goal(phone_number: str, calories: int):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET daily_goal = ? WHERE phone_number = ?",
        (calories, phone_number),
    )
    conn.commit()
    conn.close()


def update_user_profile(user_id: int, **fields) -> dict:
    """Update any subset of user profile fields.

    Supported fields: dietary_preferences, display_name, language_code, timezone.
    Returns the updated user dict.
    """
    allowed = {"dietary_preferences", "display_name", "language_code", "timezone"}
    to_update = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not to_update:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        conn.close()
        return user

    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in to_update)
    values = list(to_update.values()) + [user_id]
    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user


def log_meal(
    user_id: int,
    food_items: str,
    total_calories: int,
    image_id: str | None = None,
    notes: str = "",
    protein_g: float = 0,
    carbs_g: float = 0,
    sugar_g: float = 0,
    health_rating: int = 0,
):
    conn = get_connection()
    conn.execute(
        """INSERT INTO meals
           (user_id, food_items, total_calories, image_id, notes,
            protein_g, carbs_g, sugar_g, health_rating)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, food_items, total_calories, image_id, notes,
         protein_g, carbs_g, sugar_g, health_rating),
    )
    conn.commit()
    conn.close()


def get_user_meals_today(user_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(
        """SELECT * FROM meals
           WHERE user_id = ? AND DATE(logged_at) = ?
           ORDER BY logged_at""",
        (user_id, today),
    )
    meals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return meals


def get_user_today_calories(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(
        """SELECT COALESCE(SUM(total_calories), 0) as total
           FROM meals
           WHERE user_id = ? AND DATE(logged_at) = ?""",
        (user_id, today),
    )
    total = cursor.fetchone()["total"]
    conn.close()
    return total


def get_user_today_macros(user_id: int) -> dict:
    """Get total calories and macronutrients consumed today."""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(
        """SELECT
               COALESCE(SUM(total_calories), 0) as total_calories,
               COALESCE(SUM(protein_g), 0) as total_protein,
               COALESCE(SUM(carbs_g), 0) as total_carbs,
               COALESCE(SUM(sugar_g), 0) as total_sugar,
               COALESCE(AVG(NULLIF(health_rating, 0)), 0) as avg_health_rating
           FROM meals
           WHERE user_id = ? AND DATE(logged_at) = ?""",
        (user_id, today),
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "total_calories": row["total_calories"],
        "total_protein": round(row["total_protein"], 1),
        "total_carbs": round(row["total_carbs"], 1),
        "total_sugar": round(row["total_sugar"], 1),
        "avg_health_rating": round(row["avg_health_rating"], 1),
    }


def get_last_meal(user_id: int) -> dict | None:
    """Get the most recently logged meal for this user today."""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(
        """SELECT * FROM meals
           WHERE user_id = ? AND DATE(logged_at) = ?
           ORDER BY logged_at DESC
           LIMIT 1""",
        (user_id, today),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_meal(
    meal_id: int,
    food_items: str,
    total_calories: int,
    protein_g: float = 0,
    carbs_g: float = 0,
    sugar_g: float = 0,
    health_rating: int = 0,
):
    """Update a meal's food_items, calories, macros, and health rating."""
    conn = get_connection()
    conn.execute(
        """UPDATE meals SET food_items = ?, total_calories = ?,
           protein_g = ?, carbs_g = ?, sugar_g = ?, health_rating = ?
           WHERE id = ?""",
        (food_items, total_calories, protein_g, carbs_g, sugar_g, health_rating, meal_id),
    )
    conn.commit()
    conn.close()


def delete_meal(meal_id: int):
    """Delete a meal by ID."""
    conn = get_connection()
    conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    conn.commit()
    conn.close()


def get_user_meals_today_summary(user_id: int) -> str:
    """Return a human-readable summary of today's meals for context seeding."""
    meals = get_user_meals_today(user_id)
    if not meals:
        return ""

    lines = ["Here is what the user has already eaten today:"]
    for i, meal in enumerate(meals, 1):
        lines.append(
            f"  Meal {i} (logged at {meal['logged_at']}): "
            f"{meal['food_items']} - {meal['total_calories']} cal "
            f"(P:{meal.get('protein_g', 0)}g C:{meal.get('carbs_g', 0)}g S:{meal.get('sugar_g', 0)}g)"
        )
    total_cals = sum(m["total_calories"] for m in meals)
    lines.append(f"  Total so far: {total_cals} calories")
    return "\n".join(lines)


def get_all_active_users() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def save_daily_summary(
    user_id: int,
    total_calories: int,
    meal_count: int,
    summary_text: str,
    total_protein: float = 0,
    total_carbs: float = 0,
    total_sugar: float = 0,
    avg_health_rating: float = 0,
    daily_calorie_limit: int = 0,
):
    conn = get_connection()
    today = date.today().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO daily_summaries
           (user_id, summary_date, total_calories, meal_count, summary_text, sent_at,
            total_protein, total_carbs, total_sugar, avg_health_rating, daily_calorie_limit)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, today, total_calories, meal_count, summary_text,
         datetime.now().isoformat(),
         total_protein, total_carbs, total_sugar, avg_health_rating, daily_calorie_limit),
    )
    conn.commit()
    conn.close()


def log_weight(user_id: int, weight_kg: float):
    """Record a weight entry and update the user's current_weight."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO weight_log (user_id, weight_kg) VALUES (?, ?)",
        (user_id, weight_kg),
    )
    conn.execute(
        "UPDATE users SET current_weight = ? WHERE id = ?",
        (weight_kg, user_id),
    )
    conn.commit()
    conn.close()


def set_weight_goal(user_id: int, target_weight: float, target_date: str, tdee: int = None):
    """Set the user's weight loss/gain goal.

    Args:
        target_weight: Target weight in kg
        target_date: ISO date string (YYYY-MM-DD)
        tdee: Total Daily Energy Expenditure. If None, keeps existing value.
    """
    conn = get_connection()
    if tdee is not None:
        conn.execute(
            "UPDATE users SET target_weight = ?, target_date = ?, tdee = ? WHERE id = ?",
            (target_weight, target_date, tdee, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET target_weight = ?, target_date = ? WHERE id = ?",
            (target_weight, target_date, user_id),
        )
    conn.commit()
    conn.close()


def get_weight_history(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent weight log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM weight_log WHERE user_id = ? ORDER BY logged_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def compute_daily_calorie_limit(user_id: int) -> dict:
    """Compute the dynamic daily calorie limit from weight goal data.

    Returns a dict with daily_limit, tdee, daily_deficit, has_weight_goal,
    current_weight, target_weight, target_date, days_remaining.
    Falls back to the user's manual daily_goal when no weight goal is set.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()

    result = {
        "has_weight_goal": False,
        "daily_limit": user["daily_goal"],
        "tdee": user.get("tdee") or 2000,
        "daily_deficit": 0,
        "current_weight": user.get("current_weight"),
        "target_weight": user.get("target_weight"),
        "target_date": user.get("target_date"),
        "days_remaining": None,
    }

    cw = user.get("current_weight")
    tw = user.get("target_weight")
    td = user.get("target_date")

    if cw and tw and td:
        target = date.fromisoformat(td)
        days_remaining = (target - date.today()).days
        if days_remaining > 0:
            weight_delta = cw - tw  # positive = lose, negative = gain
            calories_per_kg = 7700
            daily_deficit = (weight_delta * calories_per_kg) / days_remaining
            tdee = user.get("tdee") or 2000
            daily_limit = round(tdee - daily_deficit)
            # Clamp to safe range
            daily_limit = max(1200, min(daily_limit, tdee + 1000))

            result["has_weight_goal"] = True
            result["daily_limit"] = daily_limit
            result["daily_deficit"] = round(daily_deficit)
            result["days_remaining"] = days_remaining

    return result


def get_weekly_consumption(user_id: int) -> dict:
    """Get total calories and macros consumed in the current week (Monday-Sunday)."""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    cursor.execute(
        """SELECT
               COALESCE(SUM(total_calories), 0) as total_calories,
               COALESCE(SUM(protein_g), 0) as total_protein,
               COALESCE(SUM(carbs_g), 0) as total_carbs,
               COALESCE(SUM(sugar_g), 0) as total_sugar,
               COUNT(*) as meal_count
           FROM meals
           WHERE user_id = ? AND DATE(logged_at) >= ?""",
        (user_id, monday.isoformat()),
    )
    row = cursor.fetchone()
    conn.close()
    days_elapsed = (today - monday).days + 1
    return {
        "total_calories": row["total_calories"],
        "total_protein": round(row["total_protein"], 1),
        "total_carbs": round(row["total_carbs"], 1),
        "total_sugar": round(row["total_sugar"], 1),
        "meal_count": row["meal_count"],
        "days_elapsed": days_elapsed,
    }


def get_monthly_consumption(user_id: int, month: int = None, year: int = None) -> dict:
    """Get total calories and macros consumed in a given month.

    Defaults to current month if not specified.
    """
    import calendar
    today = date.today()
    m = month or today.month
    y = year or today.year
    days_in_month = calendar.monthrange(y, m)[1]
    first_day = date(y, m, 1).isoformat()
    last_day = date(y, m, days_in_month).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT
               COALESCE(SUM(total_calories), 0) as total_calories,
               COALESCE(SUM(protein_g), 0) as total_protein,
               COALESCE(SUM(carbs_g), 0) as total_carbs,
               COALESCE(SUM(sugar_g), 0) as total_sugar,
               COALESCE(AVG(NULLIF(health_rating, 0)), 0) as avg_health_rating,
               COUNT(*) as meal_count
           FROM meals
           WHERE user_id = ? AND DATE(logged_at) >= ? AND DATE(logged_at) <= ?""",
        (user_id, first_day, last_day),
    )
    row = cursor.fetchone()
    conn.close()

    days_elapsed = min((today - date(y, m, 1)).days + 1, days_in_month)
    return {
        "total_calories": row["total_calories"],
        "total_protein": round(row["total_protein"], 1),
        "total_carbs": round(row["total_carbs"], 1),
        "total_sugar": round(row["total_sugar"], 1),
        "avg_health_rating": round(row["avg_health_rating"], 1),
        "meal_count": row["meal_count"],
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "month": m,
        "year": y,
    }


def update_weight_nudge_date(user_id: int):
    """Update the last_weight_nudge_date to today."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_weight_nudge_date = ? WHERE id = ?",
        (date.today().isoformat(), user_id),
    )
    conn.commit()
    conn.close()


def get_users_needing_weight_nudge() -> list[dict]:
    """Get users who have a weight goal but haven't logged weight in 10+ days."""
    conn = get_connection()
    cursor = conn.cursor()
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    cursor.execute(
        """SELECT * FROM users
           WHERE target_weight IS NOT NULL
             AND (last_weight_nudge_date IS NULL OR last_weight_nudge_date <= ?)""",
        (ten_days_ago,),
    )
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return users
