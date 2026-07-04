from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, func
from app.db.database import Base

class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    provider = Column(String(50), nullable=True)
    api_name = Column(String(100), nullable=True)
    endpoint = Column(String(255), nullable=True)
    request_count = Column(Integer, default=1, nullable=True)
    estimated_cost = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=True)

