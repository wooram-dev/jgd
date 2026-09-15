import unittest
from datetime import datetime, timezone

from commands.server_structure import build_server_structure


class FakePermissions:
    def __init__(
        self,
        *,
        view_channel: bool,
        send_messages: bool,
        read_message_history: bool,
        send_messages_in_threads: bool,
    ):
        self.view_channel = view_channel
        self.send_messages = send_messages
        self.read_message_history = read_message_history
        self.send_messages_in_threads = send_messages_in_threads


class FakeTag:
    def __init__(self, tag_id: int, name: str, emoji: str | None = None):
        self.id = tag_id
        self.name = name
        self.emoji = emoji
        self.moderated = False


class FakeChannel:
    def __init__(self, *, channel_id: int, name: str, channel_type: str, position: int):
        self.id = channel_id
        self.name = name
        self.type = channel_type
        self.position = position
        self.available_tags = None

    def permissions_for(self, role):
        if role == "everyone":
            return FakePermissions(
                view_channel=False,
                send_messages=False,
                read_message_history=False,
                send_messages_in_threads=False,
            )
        return FakePermissions(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            send_messages_in_threads=True,
        )

    def is_nsfw(self):
        return False


class FakeCategory:
    def __init__(self):
        self.id = 20
        self.name = "커뮤니티"
        self.position = 1


class FakeGuild:
    def __init__(self):
        forum = FakeChannel(channel_id=30, name="사진과-클립", channel_type="forum", position=2)
        forum.available_tags = [FakeTag(40, "게임", "🎮"), FakeTag(41, "일상")]
        forum.default_sort_order = "latest_activity"
        forum.default_layout = "gallery_view"

        self.id = 10
        self.name = "종겜동"
        self.member_count = 42
        self.default_role = "everyone"
        self.me = "bot"
        self._groups = [(FakeCategory(), [forum])]

    def by_category(self):
        return self._groups


class ServerStructureTests(unittest.TestCase):
    def test_export_omits_ids_and_private_content_by_default(self):
        result = build_server_structure(
            FakeGuild(),
            exported_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        )

        self.assertEqual(result["guild"], {"name": "종겜동", "member_count": 42})
        self.assertEqual(result["summary"]["channel_types"], {"forum": 1})
        self.assertFalse(result["privacy"]["discord_ids_included"])
        self.assertNotIn("discord_id", result["categories"][0])
        self.assertNotIn("discord_id", result["categories"][0]["channels"][0])

        serialized = repr(result).lower()
        for forbidden in ("message_content", "members", "token", "webhook"):
            self.assertNotIn(forbidden, serialized)

    def test_export_includes_forum_tags_permissions_and_optional_ids(self):
        result = build_server_structure(FakeGuild(), include_ids=True)
        category = result["categories"][0]
        forum = category["channels"][0]

        self.assertEqual(result["guild"]["discord_id"], "10")
        self.assertEqual(category["discord_id"], "20")
        self.assertEqual(forum["discord_id"], "30")
        self.assertEqual(forum["forum_tags"][0]["discord_id"], "40")
        self.assertEqual(forum["forum_tags"][0]["emoji"], "🎮")
        self.assertEqual(forum["access"]["access"], "restricted")
        self.assertTrue(forum["access"]["bot"]["can_read_history"])


if __name__ == "__main__":
    unittest.main()
