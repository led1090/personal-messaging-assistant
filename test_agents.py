"""
CLI test script to verify agent handoffs and DB operations.

Usage:
    python test_agents.py

Requires OPENAI_API_KEY in .env file.
"""

from database.models import init_db
from database.repository import get_or_create_user, get_user_today_calories, get_user_meals_today
from ai_agents import swarm_client, chat_agent, summary_agent
from context import build_context_variables

TEST_PHONE = "1234567890"


def test_greeting():
    print("\n=== Test 1: Greeting ===")
    response = swarm_client.run(
        agent=chat_agent,
        messages=[{"role": "user", "content": "Hi! What can you do?"}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_calorie_status(agent):
    print("\n=== Test 2: Calorie Status ===")
    response = swarm_client.run(
        agent=agent,
        messages=[{"role": "user", "content": "How many calories have I had today?"}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_set_goal(agent):
    print("\n=== Test 3: Set Daily Goal ===")
    response = swarm_client.run(
        agent=agent,
        messages=[{"role": "user", "content": "Set my daily goal to 1800 calories"}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_food_photo_with_text(agent):
    """Test food analysis using a text description (since we can't easily send an image in CLI)."""
    print("\n=== Test 4: Food Analysis (text-simulated) ===")
    print("NOTE: Sending a text description instead of a real photo.")
    print("      In production, this would be a base64-encoded image.")

    response = swarm_client.run(
        agent=agent,
        messages=[
            {
                "role": "user",
                "content": (
                    "I just had a plate with grilled chicken breast (about 200g), "
                    "a cup of white rice, and a side salad with olive oil dressing. "
                    "Please log this meal for me."
                ),
            }
        ],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")

    # Check DB
    user = get_or_create_user(TEST_PHONE)
    today_cals = get_user_today_calories(user["id"])
    meals = get_user_meals_today(user["id"])
    print(f"\nDB check - Total calories today: {today_cals}")
    print(f"DB check - Meals logged today: {len(meals)}")
    for meal in meals:
        print(f"  - {meal['total_calories']} cal: {meal['food_items']}")

    return response.agent


def test_text_meal_logging(agent):
    print("\n=== Test 5: Text Meal Logging ===")
    response = swarm_client.run(
        agent=agent,
        messages=[
            {
                "role": "user",
                "content": "I just had 2 scrambled eggs and a slice of whole wheat toast with butter",
            }
        ],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_weight_recording(agent):
    print("\n=== Test 6: Weight Recording ===")
    response = swarm_client.run(
        agent=agent,
        messages=[{"role": "user", "content": "My weight today is 82.5 kg"}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_weight_goal(agent):
    print("\n=== Test 7: Set Weight Goal ===")
    response = swarm_client.run(
        agent=agent,
        messages=[
            {
                "role": "user",
                "content": "I want to reach 75 kg by 2026-06-01. My TDEE is about 2200.",
            }
        ],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_monthly_report(agent):
    print("\n=== Test 8: Monthly Report ===")
    response = swarm_client.run(
        agent=agent,
        messages=[{"role": "user", "content": "Show me my monthly report"}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")
    return response.agent


def test_daily_summary():
    print("\n=== Test 9: Daily Summary ===")
    response = swarm_client.run(
        agent=summary_agent,
        messages=[{"role": "user", "content": "Generate my daily calorie summary."}],
        context_variables=build_context_variables(phone_number=TEST_PHONE),
    )
    print(f"Agent: {response.agent.name}")
    print(f"Reply: {response.messages[-1]['content']}")


def main():
    print("Initializing database...")
    init_db()

    print("Starting agent tests...\n")

    agent = test_greeting()
    agent = test_calorie_status(agent)
    agent = test_set_goal(agent)
    agent = test_food_photo_with_text(agent)
    agent = test_text_meal_logging(agent)
    agent = test_weight_recording(agent)
    agent = test_weight_goal(agent)
    agent = test_monthly_report(agent)
    test_daily_summary()

    print("\n=== All tests complete ===")


if __name__ == "__main__":
    main()
