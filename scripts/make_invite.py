\
# Generate an invite URL with selected Discord permissions using discord.py's Permissions helper.
# Usage:
#   python scripts/make_invite.py YOUR_CLIENT_ID
import sys
import discord

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_invite.py YOUR_CLIENT_ID"); return
    client_id = sys.argv[1]
    perms = discord.Permissions(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        attach_files=True,
        ban_members=True,
        moderate_members=True,
    )
    url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={perms.value}&scope=bot%20applications.commands"
    print(url)

if __name__ == "__main__":
    main()
