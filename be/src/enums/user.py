from enum import StrEnum, auto


class UserRole(StrEnum):
    GENERIC = auto()
    ADMIN = auto()


class AdminUserSortEnum(StrEnum):
    USERNAME_ASC = auto()
    USERNAME_DESC = auto()
    CREATED_AT_ASC = auto()
    CREATED_AT_DESC = auto()
