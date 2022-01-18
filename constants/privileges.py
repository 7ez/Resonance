from enum import IntFlag

class Privileges(IntFlag):
    # mans pending
    Normal = 1 << 0

    # can sign in in game
    Verified = 1 << 1

    # has to provide a liveplay
    Frozen = 1 << 2

    # special benefits ig
    Supporter = 1 << 3

    # can rank maps
    Nominator = 1 << 4

    # can do basic moderation
    Moderator = 1 << 5

    # can do advanced moderation (banning users, etc.)
    Admin = 1 << 6

    # has access to most of the commands
    Developer = 1 << 7

    # has access to every command
    Owner = 1 << 8

    # has limited amount of actions that user can do
    Restricted = 1 << 9

    # cant login in game
    Banned = 1 << 10

    Staff = Nominator | Moderator | Admin | Developer | Owner
    Disallowed = Restricted | Banned

class ClientPrivileges(IntFlag):
    Player = 1 << 0
    Moderator = 1 << 1
    Supporter = 1 << 2
    Owner = 1 << 3
    Developer = 1 << 4