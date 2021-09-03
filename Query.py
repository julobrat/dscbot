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


def getCommandParametersWithSeparator(message: str, sep: str = ' ') -> List[str]:
    words = message.split(sep)
    if len(words) > 1:
        return words[1:]
    return []


def dbCountAsString() -> str:
    return str(db['count'])


def isCommentFromDeletedChannel(comment) -> bool:
    if comment['snippet']['authorChannelUrl'] == '':
        return True
    return False


def isNumberOfParametersBetween(parameters: List, minimal: int = 0, maximal: int = 0) -> bool:
    if minimal < 0 or maximal < 0:
        raise ValueError(f'minimal {minimal} or maximal {maximal} are negative')
    if minimal > maximal:
        raise ValueError(f'Minimal {minimal} is greater than maximal {maximal}')
    numberOfParameters = len(parameters)
    if minimal <= numberOfParameters <= maximal:
        return True
    return False


class PerformedQuery:
    class Target:
        def __init__(self, videoId: str = None, channelId: str = None, idOfCommentToStopOn: str = None):
            self.videoId = videoId
            self.channelId = channelId
            self.commentToStopOnId = idOfCommentToStopOn

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

        elif self.isThisTypeOfCommand('update'):
            numberOfCommentsBefore = db['count']
            if not self.target and not self.requestParameters:
                self.setTargetAndParametersForDownloading(sourceOfData.Constants.LAST_MONSIEUR_COMMENT_ID)
            self.downloadAllCommentsFromTargetToDatabase(youtubeClient)
            await self.sendMessageOnCurrentChannel(
                'Added ' + str(db['count'] - numberOfCommentsBefore) + ' comments to database')

        elif self.isThisTypeOfCommand('show'):
            commandParameters = getCommandParametersWithSeparator(self.discordMessage.content)
            if isNumberOfParametersBetween(commandParameters, 1, 2):
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

    def setTargetAndParametersForDownloading(self, LAST_COMMENT_TO_CHECK):
        TES6_TEASER_ID = 'OkFdqqyI8y4'
        MONSIEUR_DUPOND_CHANNEL_ID = 'UCERhX03EitcqdRRPLOf5tRA'
        self.target = PerformedQuery.Target(TES6_TEASER_ID, MONSIEUR_DUPOND_CHANNEL_ID, LAST_COMMENT_TO_CHECK)

        part = 'snippet'
        textFormat = 'plainText'
        maxResults = 100
        self.setRequestParameters(part, textFormat, maxResults)

    def downloadAllCommentsFromTargetToDatabase(self, youtubeClient):
        allData = []
        while True:
            response = self.getResponseFrom(youtubeClient)
            self.requestParameters.getNewPageTokenFromResponse(response)
            data: List = self.extractCommentsFromResponseToList(response)
            for comment in data:
                allData.insert(0, comment)
            if not self.requestParameters.pageToken:
                break
        addToDatabaseFrom(allData)
        self.setNewestCommentAsOneToStopOn()

    def getResponseFrom(self, youtubeClient):
        return youtubeClient.commentThreads().list(videoId=self.target.videoId, part=self.requestParameters.part,
                                                   textFormat=self.requestParameters.textFormat,
                                                   maxResults=self.requestParameters.maxResults,
                                                   pageToken=self.requestParameters.pageToken).execute()

    def extractCommentsFromResponseToList(self, responseFromYoutube) -> List:
        data = []
        for commentThread in responseFromYoutube['items']:
            topComment = commentThread['snippet']['topLevelComment']
            if isCommentFromDeletedChannel(topComment):
                continue
            if topComment['snippet']['authorChannelId']['value'] == self.target.channelId:
                data.append(topComment)
                if topComment['id'] == self.target.commentToStopOnId:
                    self.requestParameters.resetPageToken()
                    break
        return data

    async def showCommentsFromDatabase(self, params: List):
        offset = 0
        if len(params) == 2:
            offset = int(params[1])
            if offset < 0:
                offset = abs(offset)
        maxIndex = int(params[0])

        if maxIndex > 0:
            maxIndex += offset
            if maxIndex > db['count']:
                maxIndex = db['count']

            beginning_inclusive = offset
            end_exclusive = maxIndex
            step = 1
        else:
            maxIndex = abs(maxIndex) + offset
            if maxIndex > db['count']:
                maxIndex = db['count']

            beginning_inclusive = db['count'] - 1 - offset
            end_exclusive = db['count'] - 1 - maxIndex
            step = -1

        if -1 < beginning_inclusive < db['count'] and -1 <= end_exclusive <= db['count']:
            await self.fun(beginning_inclusive, end_exclusive, step)
            await self.sendMessageOnCurrentChannel('Here you go')
            return
        await self.sendMessageOnCurrentChannel('There are no comments like these')

    async def fun(self, beginning_inclusive: int, end_exclusive: int, step: int):
        msg = ''
        for i in range(beginning_inclusive, end_exclusive, step):
            comment = db[str(i)]
            msg += convertCommentTextToStr(comment)
            if i == end_exclusive - 1 or i == end_exclusive + 1:
                break
            if not i % sourceOfData.Constants.NUMBER_OF_COMMENTS_IN_ONE_MSG:
                await self.sendMessageOnCurrentChannel(msg)
                msg = ''
        await self.sendMessageOnCurrentChannel(msg)

    def setNewestCommentAsOneToStopOn(self):
        indexOfLastComment = str(db['count'] - 1)
        self.target.commentToStopOnId = db[indexOfLastComment]['snippet']['authorChannelId']['value']


def revertIndicesInList(data: List) -> List:
    indicesToRevert = len(data) // 2
    for i in range(indicesToRevert):
        otherIndex = indicesToRevert - 1 - i
        tmp = data[i]
        data[i] = data[otherIndex]
        data[otherIndex] = tmp
    return data


def addToDatabaseFrom(data: List):
    for comment in data:
        db[dbCountAsString()] = comment
        db['count'] += 1
