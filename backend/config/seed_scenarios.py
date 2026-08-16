from sqlalchemy.orm import Session

from backend.config.database import engine
from backend.models.scenario import Scenario


scenarios = [
    {
        "name": "Real Estate Negotiation",
        "description": "A buyer and seller negotiate the price and conditions of a property.",
        "category": "real_estate",

        "agents": [
            {
                "name": "Buyer Agent",
                "role": "Buyer Representative",
                "goal": "Get the best possible property price",
                "personality": "collaborative"
            },
            {
                "name": "Seller Agent",
                "role": "Seller Representative",
                "goal": "Maximize the property selling price",
                "personality": "aggressive"
            }
        ],

        "constraints": {
            "buyer_max_budget": 500000,
            "seller_min_price": 450000,
            "max_rounds": 10
        },

        "negotiation_config": {
            "type": "price_negotiation",
            "max_rounds": 10,
            "allow_counter_offer": True
        }
    },

    {
        "name": "Business Contract Negotiation",
        "description": "Two companies negotiate the terms, price, and duration of a business contract.",
        "category": "business",

        "agents": [
            {
                "name": "Company A Agent",
                "role": "Service Buyer",
                "goal": "Reduce contract cost and secure favorable terms",
                "personality": "risk-averse"
            },
            {
                "name": "Company B Agent",
                "role": "Service Provider",
                "goal": "Maximize contract value while retaining the client",
                "personality": "collaborative"
            }
        ],

        "constraints": {
            "maximum_budget": 100000,
            "minimum_contract_value": 70000,
            "contract_duration_months": 12,
            "max_rounds": 8
        },

        "negotiation_config": {
            "type": "business_contract",
            "max_rounds": 8,
            "allow_counter_offer": True
        }
    },

    {
        "name": "Salary Negotiation",
        "description": "An employee and employer negotiate salary and benefits for a job offer.",
        "category": "career",

        "agents": [
            {
                "name": "Employee Agent",
                "role": "Employee Representative",
                "goal": "Maximize salary and benefits",
                "personality": "collaborative"
            },
            {
                "name": "Employer Agent",
                "role": "Employer Representative",
                "goal": "Hire the candidate while controlling compensation cost",
                "personality": "risk-averse"
            }
        ],

        "constraints": {
            "employee_expected_salary": 1200000,
            "employer_max_salary": 1500000,
            "minimum_salary": 900000,
            "max_rounds": 8
        },

        "negotiation_config": {
            "type": "salary_negotiation",
            "max_rounds": 8,
            "allow_counter_offer": True
        }
    }
]


def seed_scenarios():
    with Session(engine) as db:

        for scenario_data in scenarios:

            existing = (
                db.query(Scenario)
                .filter(Scenario.name == scenario_data["name"])
                .first()
            )

            if existing:
                print(f"Already exists: {scenario_data['name']}")
                continue

            scenario = Scenario(**scenario_data)

            db.add(scenario)

            print(f"Added: {scenario_data['name']}")

        db.commit()

        print("Scenario seeding completed successfully.")


if __name__ == "__main__":
    seed_scenarios()