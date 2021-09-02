# only to work with replit's secrets and db
import replit
from replit import db
# core functionalities
import discord
import googleapiclient.discovery
from keep_alive import keep_alive
# things that help in development
import os
# files from this project
from Query import PerformedQuery


class MyClient(discord.Client):
    def __init__(self, serviceName: str, version: str, developerKey: str):
        super().__init__()
        self.youtubeClient = googleapiclient.discovery.build(serviceName=serviceName, version=version,
                                                             developerKey=developerKey)

    async def on_ready(self):
        print("Logged in as", self.user.name, self.user.id)
        db['count'] = 0

    async def on_message(self, message):
        query = PerformedQuery(message)
        if query.isCommand():
            await query.resolveCommand(self.youtubeClient)


def main():
    client = MyClient(serviceName='youtube', version='v3', developerKey=os.environ['YOUTUBE_TOKEN'])
    # keep_alive()
    client.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
