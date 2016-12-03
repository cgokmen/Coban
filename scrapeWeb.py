import requests
from lxml import html
from lxml.cssselect import CSSSelector
import re
from threading import Thread
import urllib
from hurry.filesize import size

domain = "https://www.kanald.com.tr"
indexUrl = "/arka-sokaklar/bolumler?p=%d&orderby=StartDate%%20desc"

indexLinkSelector = CSSSelector(".kd-docs-section a.title")
metaContentSelector = CSSSelector("meta[itemprop='contentURL']")
hasNextSelector = CSSSelector(".load-more-container.more-button")
nameMatcher = re.compile(r'ArkaSokaklar([0-9]+)\.B\xf6l\xfcm.*', re.IGNORECASE | re.UNICODE)

def getEpisodes():
    episodes = {}
    threads = []

    # Not doing this recursively to prevent stack overflows
    hasNextPage = True
    page = 1
    while hasNextPage:
        hasNextPage = parseEpisodes(page, episodes, threads)
        page = page + 1

    print("All pages read!")


    for thread in threads:
        thread.join()

    return episodes

def getEpisodeNumberFromName(name):
    match = nameMatcher.match(name)
    number = match.group(1)
    return int(number)

def addEpisodeMediaLink(number, link, result):
    r = requests.get(link)
    tree = html.fromstring(r.content)
    tag = metaContentSelector(tree)
    try:
        mediaLink = tag[0].get("content")

        d = urllib.urlopen(mediaLink)
        fsize = int(d.info()['Content-Length'])
        d.close()

        result[number] = (mediaLink, fsize)
    except:
        print("No meta content tag for: %s at %s" % (number, link))

def parseEpisodes(n, result, threads):
    print("Reading page %d" % n)
    r = requests.get(domain + (indexUrl % n))
    tree = html.fromstring(r.content)

    episodes = indexLinkSelector(tree)
    for episode in episodes:
        name = episode.text.replace(" ", "")
        link = domain + episode.get('href')

        try:
            number = getEpisodeNumberFromName(name)
        except:
            if name == u'ArkaSokaklarSonB\xf6l\xfcm':
                number = -1
            else:
                print("Missed episode: %s" % name)
                continue

        if result.get(number) != None:
            print("There is a duplicate episode: %d" % number)
            continue

        # Get media file episode
        th = Thread(target=addEpisodeMediaLink, args=(number, link, result))
        threads.append(th)
        th.start()

    # Check if it has a next page
    hasNextPage = hasNextSelector(tree)

    if len(hasNextPage) != 0:
        return True

    return False

episodes = getEpisodes()

# Let's put the "last episode" in place (and not index -1)
maxEpisode = 0
for episode, data in episodes.iteritems():
    maxEpisode = max(maxEpisode, episode)
episodes[maxEpisode + 1] = episodes.get(-1)

totalSize = 0
# This type of loop allows us to see missing episodes too
for x in range(1, maxEpisode + 2):
    ep = episodes.get(x)
    if ep is None:
        print("%d: N/A" % x)
    else:
        link = ep[0]
        fsize = ep[1]
        print("%d: %s (size %s)" % (x, link, size(fsize)))
        totalSize = totalSize + fsize

print("\nAll episodes take up %s combined." % size(totalSize))