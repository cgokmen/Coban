import re
from threading import Thread

import requests
from lxml import html
from lxml.cssselect import CSSSelector

class KanalDParser:
    indexLinkSelector = CSSSelector(".kd-docs-section a.title")
    metaContentSelector = CSSSelector("meta[itemprop='contentURL']")
    metaPublishDateSelector = CSSSelector("meta[itemprop='datePublished']")
    hasNextSelector = CSSSelector(".load-more-container.more-button")
    nameMatcher = re.compile(r'ArkaSokaklar([0-9]+)\.B\xf6l\xfcm.*', re.IGNORECASE | re.UNICODE) # TODO: Fix this!
    domain = "https://www.kanald.com.tr"

    def __init__(self, indexUrl):
        #indexUrl = "/arka-sokaklar/bolumler?p=%d&orderby=StartDate%%20desc"
        self.indexUrl = indexUrl

    def getEpisodes(self):
        episodes = {}
        threads = []

        # Not doing this recursively to prevent stack overflows
        hasNextPage = True
        page = 1
        while hasNextPage:
            hasNextPage = self.parseEpisodes(page, episodes, threads)
            page = page + 1

        print("All pages read!")

        for thread in threads:
            thread.join()

        # Let's put the "last episode" in place (and not index -1)
        maxEpisode = 0
        for episode, data in episodes.iteritems():
            maxEpisode = max(maxEpisode, episode)
        episodes[maxEpisode + 1] = episodes.get(-1)
        del episodes[-1]

        return episodes

    @staticmethod
    def getEpisodeNumberFromName(name):
        match = KanalDParser.nameMatcher.match(name)
        number = match.group(1)
        return int(number)

    def addEpisodeMediaLink(self, number, link, result):
        r = requests.get(link)
        tree = html.fromstring(r.content)
        linkTag = self.metaContentSelector(tree)
        dateTag = self.metaPublishDateSelector(tree)
        try:
            mediaLink = linkTag[0].get("content")
            publishDate = dateTag[0].get("content")

            #d = urllib.urlopen(mediaLink)
            #fsize = int(d.info()['Content-Length'])
            #d.close()

            result[number] = (mediaLink, publishDate)
        except:
            return

    def parseEpisodes(self, n, result, threads):
        #print("Reading page %d" % n)
        r = requests.get(self.domain + (self.indexUrl % n))
        tree = html.fromstring(r.content)

        episodes = self.indexLinkSelector(tree)
        for episode in episodes:
            name = episode.text.replace(" ", "")
            link = self.domain + episode.get('href')

            try:
                number = self.getEpisodeNumberFromName(name)
            except:
                if name == u'ArkaSokaklarSonB\xf6l\xfcm':
                    number = -1
                else:
                    #print("Missed episode: %s" % name)
                    continue

            if result.get(number) != None:
                #print("There is a duplicate episode: %d" % number)
                continue

            # Get media file episode
            th = Thread(target=self.addEpisodeMediaLink, args=(number, link, result))
            threads.append(th)
            th.start()

        # Check if it has a next page
        hasNextPage = self.hasNextSelector(tree)

        if len(hasNextPage) != 0:
            return True

        return False