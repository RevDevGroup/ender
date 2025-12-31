import logging

from sqlmodel import Session, select

from app.core.db import engine, init_db
from app.models import UserPlan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_plans(session: Session) -> None:
    """Crear planes predefinidos si no existen"""
    plans_data = [
        {"name": "Free", "max_sms_per_month": 50, "max_devices": 1, "price": 0.0},
        {"name": "Basic", "max_sms_per_month": 500, "max_devices": 3, "price": 9.99},
        {"name": "Pro", "max_sms_per_month": 5000, "max_devices": 10, "price": 29.99},
        {
            "name": "Enterprise",
            "max_sms_per_month": 999999,
            "max_devices": 999,
            "price": 99.99,
        },
    ]

    for plan_data in plans_data:
        statement = select(UserPlan).where(UserPlan.name == plan_data["name"])
        existing_plan = session.exec(statement).first()
        if not existing_plan:
            plan = UserPlan(**plan_data)
            session.add(plan)
            logger.info(f"Created plan: {plan_data['name']}")
        else:
            logger.info(f"Plan {plan_data['name']} already exists")

    session.commit()


def init() -> None:
    with Session(engine) as session:
        init_db(session)
        init_plans(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
