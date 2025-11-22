"""
认证和授权依赖注入
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
try:
    import jwt
    from datetime import datetime, timedelta
except ImportError:
    jwt = None

from ...config import settings

# HTTP Bearer 认证方案
security = HTTPBearer()


class User:
    """用户模型"""
    def __init__(
        self,
        id: int,
        username: str,
        email: str,
        is_active: bool = True,
        is_superuser: bool = False,
        permissions: list = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.permissions = permissions or []

    def has_permission(self, permission: str) -> bool:
        """检查用户是否有特定权限"""
        return self.is_superuser or permission in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "permissions": self.permissions
        }


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT库未安装"
        )

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    # 这里应该使用真实的密钥，从环境变量获取
    secret_key = getattr(settings, 'secret_key', 'your-secret-key-here')
    algorithm = getattr(settings, 'algorithm', 'HS256')

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """验证令牌"""
    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT库未安装"
        )

    try:
        secret_key = getattr(settings, 'secret_key', 'your-secret-key-here')
        algorithm = getattr(settings, 'algorithm', 'HS256')

        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前用户"""
    # 简化版本，实际应该从数据库获取用户信息
    try:
        if jwt is None:
            # 如果JWT未安装，返回模拟用户
            return {
                "id": 1,
                "username": "demo_user",
                "email": "demo@example.com",
                "is_active": True,
                "is_superuser": True,
                "permissions": ["admin", "read", "write"]
            }

        payload = verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 这里应该从数据库获取用户信息
        # 暂时返回模拟用户数据
        user = User(
            id=int(user_id),
            username=payload.get("username", f"user_{user_id}"),
            email=payload.get("email", f"user_{user_id}@example.com"),
            is_active=payload.get("is_active", True),
            is_superuser=payload.get("is_superuser", False),
            permissions=payload.get("permissions", [])
        )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已被禁用"
            )

        return user.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取当前活跃用户"""
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    return current_user


def require_permission(permission: str):
    """权限装饰器"""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        if not current_user.get("is_superuser", False) and permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {permission}"
            )
        return current_user
    return permission_checker


# 常用权限检查器
require_admin = require_permission("admin")
require_write = require_permission("write")
require_read = require_permission("read")