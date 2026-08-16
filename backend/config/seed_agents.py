from backend.config.database import SessionLocal
from backend.models import Agent


agents = [
    {
        "scenario_id": 1,
        "name": "Buyer Agent",
        "role": "Buyer Representative",
        "goal": "Get the best possible property price",
        "personality": "collaborative",
    },
    {
        "scenario_id": 1,
        "name": "Seller Agent",
        "role": "Seller Representative",
        "goal": "Maximize the property selling price",
        "personality": "aggressive",
    },
    {
        "scenario_id": 2,
        "name": "Company A Agent",
        "role": "Service Buyer",
        "goal": "Reduce contract cost and secure favorable terms",
        "personality": "risk-averse",
    },
    {
        "scenario_id": 2,
        "name": "Company B Agent",
        "role": "Service Provider",
        "goal": "Maximize contract value while retaining the client",
        "personality": "collaborative",
    },
    {
        "scenario_id": 3,
        "name": "Employee Agent",
        "role": "Employee Representative",
        "goal": "Maximize salary and benefits",
        "personality": "collaborative",
    },
    {
        "scenario_id": 3,
        "name": "Employer Agent",
        "role": "Employer Representative",
        "goal": "Hire the candidate while controlling compensation cost",
        "personality": "risk-averse",
    },
]


def seed_agents():
    db = SessionLocal()

    try:
        for agent_data in agents:
            existing_agent = (
                db.query(Agent)
                .filter(
                    Agent.scenario_id == agent_data["scenario_id"],
                    Agent.name == agent_data["name"],
                )
                .first()
            )

            if existing_agent:
                print(f"Already exists: {agent_data['name']}")
                continue

            agent = Agent(**agent_data)
            db.add(agent)

            print(f"Added: {agent_data['name']}")

        db.commit()
        print("Agent seeding completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_agents()