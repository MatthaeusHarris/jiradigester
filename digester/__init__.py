__author__ = "Matt Harris <mharris@splunk.com>"
__version__ = "0.0.1"

import re
import email
from jinja2 import Template

separator = '=' * 40

class Ticket:
    def __init__(self, key):
        self.key = key
        self.changeList = []
        self.title = ""
        self.summary = ""
        self.description = ""
        self.url = ""
        self.metadata = ""

        self.shortChangeList = []
        self.truncatedChangeList = []
        print ("Ticket %s created" % key)

    def addChange(self, change):
        self.changeList.append(change)

    def addUpdate(self, update):
        self.shortChangeList.append(update.getActionLine())

        summary = update.getTicketData()
        if (summary):
            self.summary = summary

        title = update.getTitle()
        if title:
            self.title = title

        change = update.getChange()
        if change:
            self.changeList.append(change)
            self.truncatedChangeList.append(change[0:5])

        self.metadata = self.parseDescription()


    def parseDescription(self):
        if self.summary:
            metadataBlock = []
            for line in self.summary:
                if line.strip() == "":
                    break
                metadataBlock.append(line)
            return {item[0]: item[1] for item in [line.strip().split(': ') for line in metadataBlock if line.find(": ") > 0]}

    def getDictionary(self):
        changeList = ["<br />".join(changes) for changes in self.changeList]
        tempTicket = {
            "key": self.key,
            "title": self.title,
            "summary": self.summary,
            "shortChangeList": self.shortChangeList,
            "changeList": changeList,
            "metadata": self.metadata
        }
        return tempTicket


class Update:
    def __init__(self, message):
        self.message = message
        self.parsedEmail = email.message_from_string(self.message)
        self.body = self.parsedEmail.get_payload()
        print (self.body)

    def getKey(self):
        subject = self.parsedEmail['Subject']
        regex = '\((.*)\)'
        m = re.search(regex, subject)
        key = m.group(1)
        if (key != 'JIRA'):
            return key
        else:
            # It's a "mentioned you on" e-mail, which has a different format
            regex = '\mentioned you on (.*) \(JIRA\)'
            m = re.search(regex, subject)
            key = m.group(1)
            return key

    def getActor(self):
        sender = self.parsedEmail['From']
        regex = '"(.*) \(JIRA\)"'
        m = re.search(regex, sender)
        return m.group(1)

    def getActionLine(self):
        return self.matchActionLine()(0)

    def getVerb(self):
        return self.matchActionLine()(1)

    def matchActionLine(self):
        actor = self.getActor()
        key = self.getKey()
        regex = '%s (.*) %s' % (re.escape(actor), re.escape(key))
        m = re.search(regex, self.body)
        if m:
            return m.group
        else:
            # Is it a "work on ticket started by user" alert?
            regex = '(Work on %s started by .*)' % re.escape(key)
            m = re.search(regex, self.body)
            if m:
                return m.group


    def getTicketData(self):
        verb = self.getVerb()
        if (verb == 'created'):
            return self.getTicketDataForNewTicket()
        else:
            return self.getTicketDataForExistingTicket()

    def getTitle(self):
        titleMatches = [line for line in self.body.split('\r\n') if line.find("Summary:") > 0]
        if len(titleMatches) > 0:
            return titleMatches[0].split(':')[1][1:]
        elif self.getVerb() == "mentioned you on":
            return ""
        else:
            return self.getTicketData()[0]

    def getTicketDataForNewTicket(self):
        ticketData = []
        state = 'FOUND'
        for line in self.body.split('\r\n'):
            if state == 'FOUND':
                if line.startswith('--'):
                    state = 'END_FOUND'
                    break;
                if len(line) > 2:
                    ticketData.append(line)
        return ticketData

    def getTicketDataForExistingTicket(self):
        ticketData = []
        state = 'NOT_FOUND_YET'
        for line in self.body.split('\r\n'):
            if state == 'NOT_FOUND_YET':
                if line.startswith('>'):
                    state = 'FOUND'
            if state == 'FOUND':
                if line.startswith('--'):
                    state = 'END_FOUND'
                    break;
                # if len(line) > 2:
                ticketData.append(line[2:])
        return ticketData

    def getChange(self):
        changeData = []
        state = 'NOT_FOUND_YET'
        for line in self.body.split('\r\n'):
            if state == 'FOUND':
                if line.startswith('>'):
                    state = 'END_FOUND'
                    break;
                else:
                    if len(line) > 0:
                        changeData.append(line)
            if state == 'NOT_FOUND_YET':
                if ('-' * len(line)) == line and len(line) > 0:
                    state = 'FOUND'
        if (len(changeData) > 0):
            changeData[0] = self.getActionLine() + ": " + changeData[0]
        else:
            changeData.append(self.getActionLine())
        return changeData




class Digester:
    def __init__(self):
        self.tickets = {}

    def parseEmail(self, message):
        update = Update(message)
        key = update.getKey()

        if (not self.tickets.has_key(key)):
            self.tickets[key] = Ticket(key)
        self.tickets[key].addUpdate(update)

    def getDigest(self):
        returnString = "JIRA DIGEST\r\n%s\r\n\r\n" % separator
        returnString = "SUMMARY:\r\n"
        for key, ticket in self.tickets.iteritems():
            returnString = returnString + \
                key + ": " + ticket.title + ": " + ticket.title + "\r\n"
            for change in ticket.shortChangeList:
                returnString = returnString + \
                    change + "\r\n"
            returnString = returnString + separator + "\r\n\r\n"

        returnString = returnString + self.getMediumDigest() + self.getLongDigest()
        return returnString

    def getMediumDigest(self):
        returnString = "\r\nMEDIUM SUMMARY:\r\n%s\r\n" % separator
        for key, ticket in self.tickets.iteritems():
            returnString = returnString + \
                           key + ": " + ticket.title + "\r\n\r\n"
            for change in ticket.truncatedChangeList:
                returnString = returnString + \
                               "\r\n".join(change) + "\r\n"
            returnString = returnString + separator + "\r\n\r\n"
        return returnString

    def getLongDigest(self):
        returnString = "\r\nLONG SUMMARY:\r\n%s\r\n" % separator
        for key, ticket in self.tickets.iteritems():
            returnString = returnString + \
                key + ": " + ticket.title + "\r\n\r\n"
            for change in ticket.changeList:
                returnString = returnString + \
                    "\r\n".join(change) + "\r\n"
            returnString = returnString + separator + "\r\n\r\n"
        return returnString

    def templateDigest(self, template):
        with open(template, 'r') as templateFile:
            templateText = templateFile.read()
        jinjaTemplate = Template(templateText)
        tickets = self.prepareTicketList()
        return jinjaTemplate.render({'tickets': tickets})

    def prepareTicketList(self):
        tickets = [ticket.getDictionary() for ticket in self.tickets.itervalues()]
        return tickets