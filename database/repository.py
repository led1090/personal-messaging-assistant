from datetime import date, datetime
from database.models import get_connection


def get_or_create_user(phone_number: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()

    if row:
        user = dict(row)
        conn.close()
        return user

    cursor.execute(
        "INSERT INTO users (phone_number) VALUES (?)",
        (phone_number,),
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


def log_meal(
    user_id: int,
    food_items: str,
    total_calories: int,
    image_id: str | None = None,
    notes: str = "",
    protein_g: float = 0,
    carbs_g: float = 0,
    sugar_g: float = 0,
):
    conn = get_connection()
    conn.execute(
        """INSERT INTO meals
           (user_id, food_items, total_calories, image_id, notes, protein_g, carbs_g, sugar_g)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, food_items, total_calories, image_id, notes, protein_g, carbs_g, sugar_g),
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
               COALESCE(SUM(sugar_g), 0) as total_sugar
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
):
    """Update a meal's food_items, calories, and macros."""
    conn = get_connection()
    conn.execute(
        """UPDATE meals SET food_items = ?, total_calories = ?,
           protein_g = ?, carbs_g = ?, sugar_g = ?
           WHERE id = ?""",
        (food_items, total_calories, protein_g, carbs_g, sugar_g, meal_id),
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
):
    conn = get_connection()
    today = date.today().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO daily_summaries
           (user_id, summary_date, total_calories, meal_count, summary_text, sent_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, today, total_calories, meal_count, summary_text, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
