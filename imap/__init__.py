__author__ = "Matt Harris <mharris@splunk.com>"
__version__ = "0.0.1"

import datetime
import imaplib
import time
import ConfigParser
import getpass
from email.mime.text import MIMEText

class ImapConnection:
    def __init__(self, configFile):
        config = ConfigParser.ConfigParser()
        config.readfp(open(configFile))
        self.server = config.get('mailserver', 'server')
        self.username = config.get('mailserver', 'username')
        self.port = config.get('mailserver', 'port')
        self.jiraFolder = config.get('mailserver', 'jirafolder')
        self.inboxFolder = config.get('mailserver', 'inboxfolder')
        self.password = getpass.getpass("Please enter password for %s: " % self.username)

        self.imap = imaplib.IMAP4_SSL(self.server, self.port)
        self.imap.login(self.username, self.password)
        self.imap.select(self.jiraFolder)

    def connectToImap(self):
        print("Connecting to %s:%s as %s" % (self.server, self.port, self.username))
        self.imap = imaplib.IMAP4_SSL(self.server, self.port)
        self.imap.login(self.username, self.password)
        self.imap.select(self.jiraFolder)

    def fetchMessageIdsForDate(self, fromDate):
        searchSince = fromDate
        searchBefore = (datetime.datetime.strptime(fromDate, "%d-%b-%Y") + datetime.timedelta(days=1))\
            .strftime("%d-%b-%Y")
        searchString = '(SINCE "%s" BEFORE "%s")' % (searchSince, searchBefore)
        self.connectToImap()
        print("Searching on searchString: %s" % searchString)
        status, idList = self.imap.search(None, searchString)
        print(status, idList)
        return idList[0].split(' ')

    def fetchMessageIdsForToday(self):
        return self.fetchMessagesForDate(time.strftime("%d-%b-%Y"))

    def fetchMessageTextById(self, id):
        status, message = self.imap.fetch(id, '(RFC822)')
        return message[0][1]

    def fetchMessageTextByIds(self, idList):
        print("Fetching list %s" % idList)
        if (len(idList) == 0):
            return {}
        return {id: self.fetchMessageTextById(id) for id in idList}

    def createMessage(self, message):
        msg = MIMEText(message)
        msg['Subject'] = "JIRA Digest"
        msg['From'] = self.username
        msg['To'] = self.username
        print("Creating digest e-mail")
        self.imap.append(self.inboxFolder, None, None, msg.as_string())

