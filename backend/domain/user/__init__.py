# input: 本包内 entity/repository/service
# output: User 实体, UserRepository 接口, UserDomainService
# owner: wanhua.gu
# pos: 领域层 - 用户聚合公共出口；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""User aggregate public exports."""

from domain.user.entity import User
from domain.user.repository import UserRepository
from domain.user.service import UserDomainService

__all__ = ["User", "UserRepository", "UserDomainService"]
