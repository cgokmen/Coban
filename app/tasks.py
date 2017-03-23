from parsers import KanalDParser
from models import Series, Season, Episode, ChannelEnum
from feedgen.feed import FeedGenerator
import tvdb_api
import datetime
from dateutil.parser import parse

MAX_GAP = datetime.timedelta(days=60) # Two months of no new episodes mean new season

def mainTask(session):
    shows = session.query(Series)

    currentTime = None
    tvdb = tvdb_api.Tvdb()

    feeds = {}

    for show in shows:
        processTvdbSeasons(session, show, tvdb) # Start by synchronizing the seasons with any Tvdb updates

        importNewEpisodes(session, show, currentTime, tvdb) # Import the episodes

        recalculateSeasons(session, show, MAX_GAP) # Recalculate predicted seasons based on time gaps

        feeds[show.friendlyName] = getRSSFeed(show) # Put the RSS feed into the return dictionary

    return feeds


def importNewEpisodes(session, series, currentTime, tvdb):
    indexURL = series.index_url
    parser = None

    if series.channel == ChannelEnum.KanalD:
        parser = KanalDParser(indexURL)

    # TODO: Add other channels?

    episodes = parser.getEpisodes()

    # Iterate episodes to see if we're missing any
    for episodeNumber, (episodeURL, datePublished) in episodes.iteritems():
        query = session.query(Episode).filter(Episode.season.series == series, Episode.number == episodeNumber)
        if query.count() == 0:
            # Create the episode
            episode = Episode(number = episodeNumber, media_link = episodeURL, date_aired = datePublished, date_found = currentTime, series_id = series.id)

            # Find which season to put this shit in
            assignEpisodeToSeason(series, episode)

            # Also attempt to find TVDB release date
            date_aired = retrieveTvdbReleaseDate(episode, tvdb)

            if date_aired is not None:
                episode.date_aired = date_aired

            session.add(episode)
        else:
            # We want to check if the URL has changed
            episode = query.first()

            if episode.media_link != episodeURL:
                # TODO: The media link has changed. Should we log this?
                episode.media_link = episodeURL

            # Also check if a tvdb release date has appeared
            date_aired = retrieveTvdbReleaseDate(episode, tvdb)

            if date_aired is not None:
                episode.date_aired = date_aired

    session.commit()

def processTvdbSeasons(session, series, tvdb):
    # TODO: Implement this
    # We can assume that the TVDB is definitive for all non-present seasons.
    pass

def retrieveTvdbReleaseDate(episode, tvdb):
    # If the season is not on Tvdb yet, we return None
    if not episode.season.found_on_tvdb:
        return None

    # Otherwise, we're ready to try to pull it
    tvdbId = episode.season.series.tvdb_id
    seasonNo = episode.season.season_number

    tvdbSeason = tvdb[tvdbId][seasonNo]

    # Attempt to find this episode
    episodeNo = episode.number - episode.season.season_starting_episode_number + 1
    tvdbEpisode = tvdbSeason[episodeNo]

    # If its not found, return None
    if tvdbEpisode is None:
        return None

    # If it does not have an aired date, return None
    dateAiredString = tvdbEpisode.get('firstAired')
    if dateAiredString is None:
        return None

    # Convert that to a datetime obj
    dateAired = parse(dateAiredString)
    if dateAired is None:
        return None

    return dateAired

def recalculateSeasons(session, series, maxGap):
    # This process splits existing predicted seasons depending on the amount of time
    # that has passed between the release dates of two episodes. Note that we make no
    # attempt of remerging previously broken-off seasons, so if something got fucked up
    # there is not much to do apart from waiting for tvdb to get us a fix.

    # We start by sorting the episodes according to their number
    episodes = sorted(series.episodes, key=(lambda key: key.number))

    # First task: if two episodes are in two separate predictive seasons but don't have a big enough gap
    # between them, we merge the seasons back together. This only happens if the aired dates were updated
    # after a prediction was made.

    # TODO: Make the system email the administrator once a predictive season has ended. This way we can make sure to
    # have only one predictive season at any time by getting him to finalize the season.

    prevEpisode = None

    # TODO: Implement this, when will it fail, what are some assumptions we can make?
    for episode in episodes:
        if prevEpisode is not None:
            # Is the previous episode in a predictive season?
            if prevEpisode.season.isPrediction:
                # Is this episode in a predictive season?
                if episode.season.isPrediction:
                    # Check the time difference between them
                    deltaTime = episode.date_aired - prevEpisode.date_aired

                    # If it's smaller than the maxGap, we pull these seasons back together


        prevEpisode = episode

def reassignAllEpisodesToSeasons(session, series):
    for episode in series.episodes:
        assignEpisodeToSeason(series, episode)

    session.commit()

def assignEpisodeToSeason(series, episode):
    seasons = sorted(series.seasons, key=lambda season: season.season_ending_episode)
    seasonToAddInto = None

    for season in seasons:
        if season.season_starting_episode_number <= episode.number and episode.number <= season.season_ending_episode_number_episode:
            seasonToAddInto = season
            break

    if seasonToAddInto is None:
        # TODO: Throw some sort of Error because of no season to insert this into: this should never happen!
        pass

    episode.season_id = seasonToAddInto.id

def getRSSFeed(series):
    seriesName = series.name

    fg = FeedGenerator()
    fg.title("%s Bolumleri" % seriesName)
    fg.author({'name': 'Riperion Medya', 'email': 'riperion.inc@gmail.com'})

    for season in series.seasons:
        seasonNumber = season.season_number
        for episode in season.episodes:
            link = episode.media_link
            date = episode.date_found
            episodeNoInSeason = episode.number - season.season_starting_episode_number + 1

            fe = fg.add_entry()
            fe.title("%s %d. Bolum (S%02dE%02d)" % (seriesName, episode.number, seasonNumber, episodeNoInSeason))
            fe.published(date)
            fe.link(link)

    return fg.rss_str(pretty=True)