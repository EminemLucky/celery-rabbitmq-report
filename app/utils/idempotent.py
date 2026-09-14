from app import db
from app.models import IdempotentRecord
from sqlalchemy.exc import IntegrityError


def try_acquire(idem_key: str) -> bool:
    """
    尝试占位。返回 True 表示第一次处理；False 表示重复请求。
    """
    record = IdempotentRecord(idem_key=idem_key)
    try:
        db.session.add(record)
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False