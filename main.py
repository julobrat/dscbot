# only to work with replit's secrets and db
import replit
from replit import db
# core functionalities
import discord
import googleapiclient.discovery
from keep_alive import keep_alive
# things that help in development
import os
from typing import List
import help


# TODO: zrób funkcję do wyświetlanie komentarzy z danego przedziału, w tym szczególny przypadek dla 1 komentarza np. 5. od końca


def getHelp() -> str:
    return help.helpMessage


def tryToFindComment(channelId, response):
    for comment in response['items']:
        topComment = comment['snippet']['topLevelComment']
        topCommentChannelId = topComment['snippet']['authorChannelId']['value']
        if topCommentChannelId == channelId:
            return topComment
    return None


def makeStrFromComments(comments: List) -> str:
    msg = str()
    for comment in comments:
        msg += f"```{comment['snippet']['textDisplay']}```"
    return msg


class RequestParameters:
    def __init__(self, videoId: str = None, part: str = None, textFormat: str = None, pageToken: str = None,
                 maxResults: int = 20):
        self.videoId = videoId
        self.part = part
        self.textFormat = textFormat
        self.pageToken = pageToken
        self.maxResults = maxResults


class MyClient(discord.Client):
    def __init__(self, serviceName: str, version: str, developerKey: str):
        super().__init__()
        self.youtubeClient = googleapiclient.discovery.build(serviceName=serviceName, version=version,
                                                             developerKey=developerKey)
        self.requestParameters = RequestParameters()
        self.timeToShowLatestComment: str = '00:00:00'
        self.channelToShowLatestComment = None
        self.turnedOn: bool = False
        self.latestComment: str = ""

    async def on_ready(self):
        print("Logged in as", self.user.name, self.user.id)

    async def on_message(self, message):
        if message.content.startswith('!'):
            await self.resolveCommand(message)
        if self.turnedOn:
            await self.tryToAutomaticalyGetLatestCommentWhenItChanges()

    async def tryToAutomaticalyGetLatestCommentWhenItChanges(self):
        self.requestParameters.pageToken = None
        comment = self.getLatestComments(1)
        if comment != self.latestComment:
            self.latestComment = comment
            await self.channelToShowLatestComment.send(makeStrFromComments(comment))

    async def resolveCommand(self, message):
        commandWords: List[str] = message.content[1:].split(sep=' ')
        msg = "It just doesn't work"
        if message.content.startswith('!greet'):
            msg = 'I greet you'
        if message.content.startswith('!comment'):
            msg = self.executeCommentCmd(commandWords[1:])
        if message.content.startswith('!help'):
            msg = getHelp()
        if message.content.startswith('!turn'):
            msg = self.switchDailyComment(message)
        if message.content.startswith('!skyrim'):
            msg = 'Here you go pretty sir\n' + 'https://steamcommunity.com/app/72850/discussions/0/1692669912384122796/'  # original Skyrim link
        await message.channel.send(msg)

    def switchDailyComment(self, message) -> str:
        if 'on' in message.content:
            self.turnedOn = True
            self.channelToShowLatestComment = message.channel
            return "Turned daily comment on"
        if 'off' in message.content:
            self.turnedOn = False
            self.channelToShowLatestComment = None
            self.latestComment = ""
            return "Turned daily comment off"
        return "What do you want to turn? Myself on?"

    def executeCommentCmd(self, words: List[str]):
        n = 1
        self.requestParameters.maxResults = 20
        if len(words) > 0:
            n = int(words[0])
            self.requestParameters.maxResults = 1
        comments: List = self.getLatestComments(n)
        return makeStrFromComments(comments)

    def getLatestComments(self, n) -> List[str]:
        self.requestParameters.videoId = 'OkFdqqyI8y4'
        self.requestParameters.part = 'snippet'
        self.requestParameters.textFormat = 'plainText'

        MONSIEUR_DUPOND_CHANNEL_ID = 'UCERhX03EitcqdRRPLOf5tRA'
        comments = []
        self.requestParameters.pageToken = None
        for i in range(n):
            comments.append(self.findPreviousCommentFrom(MONSIEUR_DUPOND_CHANNEL_ID))
        self.requestParameters.pageToken = None
        return comments

    def getResponseWithParameters(self):
        params = self.requestParameters
        if params.pageToken:
            return self.youtubeClient.commentThreads().list(videoId=params.videoId, part=params.part,
                                                            textFormat=params.textFormat,
                                                            pageToken=params.pageToken,
                                                            maxResults=params.maxResults).execute()
        return self.youtubeClient.commentThreads().list(videoId=params.videoId, part=params.part,
                                                        textFormat=params.textFormat,
                                                        maxResults=params.maxResults).execute()

    def findPreviousCommentFrom(self, channelId):
        comment = None
        while not comment:
            response = self.getResponseWithParameters()
            comment = tryToFindComment(channelId, response)
            self.requestParameters.pageToken = response['nextPageToken']
            if comment:
                return comment


def main():
    client = MyClient(serviceName='youtube', version='v3', developerKey=os.environ['YOUTUBE_TOKEN'])
    # keep_alive()
    client.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
