# only to work with replit's secrets and db
import replit
from replit import db
# core functionalities
import discord
# things that help in development
from typing import List
# files from this project
import sourceOfData


def getHelp() -> str:
    return sourceOfData.helpMessage


def makeStrFromComments(comments: List) -> str:
    msg = str()
    for comment in comments:
        msg += convertCommentTextToStr(comment)
    return msg


def convertCommentTextToStr(comment) -> str:
    return f"```{comment['snippet']['textDisplay']}```"


def getCommandParameters(message: str) -> List[str]:
    words = message.split(' ')
    if len(words) > 1:
        return words[1:]
    return ['0']


class PerformedQuery:
    class Target:
        def __init__(self, videoId: str = None, channelId: str = None):
            self.videoId = videoId
            self.channelId = channelId

    class RequestParameters:
        def __init__(self, part: str = None, textFormat: str = None, maxResults: int = 20, pageToken: str = None):
            self.part = part
            self.textFormat = textFormat
            self.maxResults = maxResults
            self.pageToken = pageToken

        def resetPageToken(self):
            self.pageToken = None

        def getNewPageTokenFromResponse(self, response):
            try:
                self.pageToken = response['nextPageToken']
            except KeyError:
                self.resetPageToken()


    def __init__(self, message: discord.Message):
        self.discordMessage: discord.Message = message
        self.target = None
        self.requestParameters = None

    def setTarget(self, videoId: str, channelId: str):
        self.target = self.Target(videoId, channelId)

    def setRequestParameters(self, part: str = None, textFormat: str = None, maxResults=20, pageToken: str = None):
        self.requestParameters = self.RequestParameters(part, textFormat, maxResults, pageToken)

    def isCommand(self) -> bool:
        if self.discordMessage.content.startswith(sourceOfData.Constants.COMMAND_PROMPT):
            return True
        return False

    def isThisTypeOfCommand(self, typeOfCommand: str) -> bool:
        if self.discordMessage.content.startswith(sourceOfData.Constants.COMMAND_PROMPT + typeOfCommand):
            return True
        return False

    async def sendMessageOnCurrentChannel(self, msg: str):
        await self.discordMessage.channel.send(msg)

    async def resolveCommand(self, youtubeClient):
        if self.isThisTypeOfCommand('greet'):
            await self.sendGreetings()
        elif self.isThisTypeOfCommand('download'):
            self.setTargetAndParametersForDownloading()
            self.downloadAllCommentsFromTargetToDatabase(youtubeClient)
            await self.sendMessageOnCurrentChannel('Downloaded ' + str(db['count']) + ' comments')
        elif self.isThisTypeOfCommand('show'):
            commandParameters = getCommandParameters(self.discordMessage.content)
            await self.showCommentsFromDatabase(commandParameters)
        elif self.isThisTypeOfCommand('skyrim'):
            await self.sendSkyrimLink()
        elif self.isThisTypeOfCommand('help'):
            await self.sendHelpInfo()
        else:
            incorrectCommandMsg = "It just doesn't work"
            await self.sendMessageOnCurrentChannel(incorrectCommandMsg)

    async def sendHelpInfo(self):
        info = getHelp()
        await self.sendMessageOnCurrentChannel(info)

    async def sendGreetings(self):
        await self.sendMessageOnCurrentChannel('I greet you')

    async def sendSkyrimLink(self):
        link = sourceOfData.skyrimLink
        msg = sourceOfData.skyrimLinkMessage
        await self.sendMessageOnCurrentChannel(msg + link)

    def setTargetAndParametersForDownloading(self):
        TES6_TEASER_ID = 'OkFdqqyI8y4'
        MONSIEUR_DUPOND_CHANNEL_ID = 'UCERhX03EitcqdRRPLOf5tRA'
        self.setTarget(videoId=TES6_TEASER_ID, channelId=MONSIEUR_DUPOND_CHANNEL_ID)
        part = 'snippet'
        textFormat = 'plainText'
        maxResults = 100
        self.setRequestParameters(part, textFormat, maxResults)

    def downloadAllCommentsFromTargetToDatabase(self, youtubeClient):
        while True:
            response = self.getResponseFrom(youtubeClient)
            self.requestParameters.getNewPageTokenFromResponse(response)
            self.extractCommentsToDatabaseFrom(response)
            if not self.requestParameters.pageToken:
                return

    def getResponseFrom(self, youtubeClient):
        return youtubeClient.commentThreads().list(videoId=self.target.videoId, part=self.requestParameters.part,
                                                   textFormat=self.requestParameters.textFormat,
                                                   maxResults=self.requestParameters.maxResults,
                                                   pageToken=self.requestParameters.pageToken).execute()

    def extractCommentsToDatabaseFrom(self, responseFromYoutube):
        for commentThread in responseFromYoutube['items']:
            topComment = commentThread['snippet']['topLevelComment']
            if topComment['snippet']['authorChannelId']['value'] == self.target.channelId:
                db[db['count']] = topComment
                db['count'] += 1
                if topComment['id'] == 'UgwSrnCSFi1guLmpS354AaABAg':
                    self.requestParameters.resetPageToken()


    async def showCommentsFromDatabase(self, params: List):
        numberOfSteps = int(params[0])
        for i in range(numberOfSteps):
            comment = db[i]
            await self.sendMessageOnCurrentChannel(convertCommentTextToStr(comment))
