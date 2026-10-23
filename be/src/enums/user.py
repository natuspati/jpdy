from enum import StrEnum, auto


class UserRole(StrEnum):
    GENERIC = auto()
    ADMIN = auto()


class AdminUserSortEnum(StrEnum):
    USERNAME_ASC = auto()
    USERNAME_DESC = auto()
    ROLE_ASC = auto()
    ROLE_DESC = auto()
    CREATED_AT_ASC = auto()
    CREATED_AT_DESC = auto()
    LOBBIES_PLAYED_ASC = auto()
    LOBBIES_PLAYED_DESC = auto()
    LOBBIES_HOSTED_ASC = auto()
    LOBBIES_HOSTED_DESC = auto()
