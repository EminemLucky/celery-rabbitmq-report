from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379/2",
    default_limits=["1000/hour"],
)

# WebSocket，多 worker 用 Redis 做消息队列
socketio = SocketIO(
    cors_allowed_origins="*",
    message_queue="redis://redis:6379/3",
    async_mode="threading",
)