import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User, UserPlan, UserQuota


class QuotaService:
    @staticmethod
    def get_user_quota(*, session: Session, user_id: uuid.UUID) -> dict[str, Any]:
        """Obtener información de cuota del usuario"""
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        quota = user.quota
        if not quota:
            # Crear quota si no existe
            quota = QuotaService._create_default_quota(session=session, user_id=user_id)

        plan = session.get(UserPlan, quota.plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Plan no encontrado",
            )

        # Calcular fecha de reset (próximo día configurado del mes)
        reset_date = None
        if quota.last_reset_date:
            from datetime import date

            # Calcular próximo mes
            if quota.last_reset_date.month == 12:
                next_year = quota.last_reset_date.year + 1
                next_month = 1
            else:
                next_year = quota.last_reset_date.year
                next_month = quota.last_reset_date.month + 1
            try:
                reset_date = date(
                    next_year, next_month, settings.QUOTA_RESET_DAY
                ).isoformat()
            except ValueError:
                # Si el día no existe en el mes, usar el último día del mes
                from calendar import monthrange

                last_day = monthrange(next_year, next_month)[1]
                reset_date = date(
                    next_year, next_month, min(settings.QUOTA_RESET_DAY, last_day)
                ).isoformat()

        return {
            "plan": plan.name,
            "sms_sent_this_month": quota.sms_sent_this_month,
            "max_sms_per_month": plan.max_sms_per_month,
            "devices_registered": quota.devices_registered,
            "max_devices": plan.max_devices,
            "reset_date": reset_date,
        }

    @staticmethod
    def check_sms_quota(*, session: Session, user_id: uuid.UUID, count: int) -> bool:
        """Verificar si usuario puede enviar N SMS"""
        quota = QuotaService._get_or_create_quota(session=session, user_id=user_id)
        plan = session.get(UserPlan, quota.plan_id)
        if not plan:
            return False

        if quota.sms_sent_this_month + count > plan.max_sms_per_month:
            available = plan.max_sms_per_month - quota.sms_sent_this_month
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Solo puedes enviar {available} SMS más este mes",
                    "quota_type": "sms_monthly",
                    "limit": plan.max_sms_per_month,
                    "used": quota.sms_sent_this_month,
                    "available": available,
                    "reset_date": (
                        QuotaService._calculate_reset_date(quota.last_reset_date)
                        if quota.last_reset_date
                        else None
                    ),
                    "upgrade_url": "/api/v1/sms/plans",
                },
            )
        return True

    @staticmethod
    def check_device_quota(*, session: Session, user_id: uuid.UUID) -> bool:
        """Verificar si usuario puede registrar otro dispositivo"""
        quota = QuotaService._get_or_create_quota(session=session, user_id=user_id)
        plan = session.get(UserPlan, quota.plan_id)
        if not plan:
            return False

        if quota.devices_registered >= plan.max_devices:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Límite de {plan.max_devices} dispositivos alcanzado",
                    "quota_type": "devices",
                    "limit": plan.max_devices,
                    "used": quota.devices_registered,
                    "available": 0,
                    "upgrade_url": "/api/v1/sms/plans",
                },
            )
        return True

    @staticmethod
    def increment_sms_count(
        *, session: Session, user_id: uuid.UUID, count: int
    ) -> None:
        """Incrementar contador de SMS enviados"""
        quota = QuotaService._get_or_create_quota(session=session, user_id=user_id)
        quota.sms_sent_this_month += count
        session.add(quota)
        session.commit()

    @staticmethod
    def increment_device_count(*, session: Session, user_id: uuid.UUID) -> None:
        """Incrementar contador de dispositivos"""
        quota = QuotaService._get_or_create_quota(session=session, user_id=user_id)
        quota.devices_registered += 1
        session.add(quota)
        session.commit()

    @staticmethod
    def decrement_device_count(*, session: Session, user_id: uuid.UUID) -> None:
        """Decrementar contador de dispositivos"""
        quota = QuotaService._get_or_create_quota(session=session, user_id=user_id)
        if quota.devices_registered > 0:
            quota.devices_registered -= 1
            session.add(quota)
            session.commit()

    @staticmethod
    def _get_or_create_quota(*, session: Session, user_id: uuid.UUID) -> UserQuota:
        """Obtener o crear quota del usuario"""
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        if user.quota:
            return user.quota

        return QuotaService._create_default_quota(session=session, user_id=user_id)

    @staticmethod
    def _calculate_reset_date(last_reset_date: datetime) -> str:
        """Calcular fecha de próximo reset"""
        from calendar import monthrange
        from datetime import date

        if last_reset_date.month == 12:
            next_year = last_reset_date.year + 1
            next_month = 1
        else:
            next_year = last_reset_date.year
            next_month = last_reset_date.month + 1

        try:
            reset_date = date(next_year, next_month, settings.QUOTA_RESET_DAY)
        except ValueError:
            last_day = monthrange(next_year, next_month)[1]
            reset_date = date(
                next_year, next_month, min(settings.QUOTA_RESET_DAY, last_day)
            )

        return reset_date.isoformat()

    @staticmethod
    def _create_default_quota(*, session: Session, user_id: uuid.UUID) -> UserQuota:
        """Crear quota por defecto para usuario"""
        # Buscar plan por defecto
        plan_name = settings.DEFAULT_PLAN.lower()
        statement = select(UserPlan).where(UserPlan.name.ilike(f"%{plan_name}%"))
        plan = session.exec(statement).first()

        if not plan:
            # Si no existe, crear plan Free
            plan = UserPlan(
                name="Free",
                max_sms_per_month=50,
                max_devices=1,
                price=0.0,
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)

        quota = UserQuota(
            user_id=user_id,
            plan_id=plan.id,
            sms_sent_this_month=0,
            devices_registered=0,
            last_reset_date=datetime.utcnow(),
        )
        session.add(quota)
        session.commit()
        session.refresh(quota)
        return quota
