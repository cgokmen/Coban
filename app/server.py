import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twisted.python import log
from twisted.web.resource import Resource, NoResource
from twisted.web.server import Site
from twisted.web.util import redirectTo

from cobanlib import tasks

sqlPath = '/data/data.db'
engine = create_engine("sqlite:///" + sqlPath, connect_args={'check_same_thread': False})
DBSession = sessionmaker(bind=engine)

class HomeResource(Resource):
    def render_GET(self, request):
        return redirectTo("feed.rss", request)

class RSSResource(Resource):
    isLeaf = True

    def __init__(self, session):
        Resource.__init__(self)
        self.session = session
        self.feeds = {}

    def render_GET(self, request):
        friendlyName = None # TODO: Get the friendly name from the request
        feed = self.feeds.get(friendlyName)

        if feed is not None:
            return self.currentRSS
        else:
            return NoResource(message="The series %s was not found" % friendlyName)

    def refreshCache(self):
        self.feeds = tasks.mainTask(self.session)
        return


if __name__ == '__main__':
    log.startLogging(sys.stdout)

    # TODO: Read database URL here

    session = DBSession()
    root = HomeResource()
    rssResource = RSSResource(session)
    root.putChild("feed.rss", rssResource)

    from twisted.internet import task
    from twisted.internet import reactor

    l = task.LoopingCall(rssResource.refreshCache, session, rssResource)
    l.start(300.0)  # call every 5 minutes

    reactor.listenTCP(80, Site(root))
    reactor.run()