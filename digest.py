__author__ = "Matt Harris <mharris@splunk.com>"
__version__ = "0.0.1"

import imap
import digester
import time
import datetime

class Runner:
    def __init__(self):
        self.fetcher = imap.ImapConnection('config')


    def process(self, date="today"):
        if date == "today":
            date = datetime.datetime.strftime(datetime.datetime.now(), "%d-%b-%Y")
        messageIds = self.fetcher.fetchMessageIdsForDate(date)
        messageTexts = self.fetcher.fetchMessageTextByIds(messageIds)
        processor = digester.Digester()
        for message in messageTexts.itervalues():
            processor.parseEmail(message)
        print "\n\n\n\n"
        # digest = processor.getDigest()
        # print (digest)
        # self.fetcher.createMessage(digest)
        digest = processor.templateDigest('templates/test.j2')
        self.fetcher.createMessage(digest, "html")
        print(digest)

    def run(self, delay):
        while True:
            self.process('today')
            time.sleep(delay)

if __name__ == '__main__':
    runner = Runner()
    runner.run(3600)
