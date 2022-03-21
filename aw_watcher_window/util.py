"""
Added python file for the ERC project -Disconnect-
The intention of this function is to map window titles from browser apps into general categories (e.g Facebook > Social)

-- Coded by Simon Perneel
-- mailto:Simon.Perneel@UGent.be
"""

# Global variables
# define mapping dict from url to category
url_to_cat_map = dict.fromkeys(['www.vrt.be', 'www.hln.be', 'www.nieuwsblad.be', 'www.hln.be', 'www.demorgen.be', 'www.standaard.be',
                                'www.mo.be', 'www.knack.be', 'www.bbc.com', 'www.aljazeera.com', 'www.theguardian.com', 'edition.cnn.com',
                                'www.foxnews.com', 'www.humo.be'], 'News')
url_to_cat_map.update(dict.fromkeys(['www.facebook.com'], 'Facebook'))
url_to_cat_map.update(dict.fromkeys(['www.instagram.com'], 'Instagram'))
url_to_cat_map.update(dict.fromkeys(['www.twitter.com'], 'Twitter'))
url_to_cat_map.update(dict.fromkeys(['www.tiktok.com'], 'TikTok'))
url_to_cat_map.update(dict.fromkeys(['www.youtube.com'], 'Youtube'))
url_to_cat_map.update(dict.fromkeys(['www.discord.com', 'www.snapchat.com', 'www.bere.al'], 'Social Media - Other'))
url_to_cat_map.update(dict.fromkeys(['www.messenger.com', 'www.web.whatsapp.com'], 'Messaging'))
url_to_cat_map.update(dict.fromkeys(['www.reddit.com', 'www.9gag.com', 'www.tumblr.com', 'www.blogspot.com'], 'Forums & Blogs'))
url_to_cat_map.update(dict.fromkeys(['www.mail.google.com', 'www.outlook.office365.com', 'www.yahoo.com', 'www.webmail.scarlet.be'], 'Email'))
url_to_cat_map.update(dict.fromkeys(['www.zoom.us, meet.google.com'], 'Videoconferencing'))
url_to_cat_map.update(dict.fromkeys(['calendar.google.com', 'www.teams.microsoft.com', 'www.docs.google.com', 'www.deepl.com', 'www.translate.google.com', 'www.miro.com/login/'], 'Work & Productivity'))
url_to_cat_map.update(dict.fromkeys(['www.streamz.be', 'www.vtm.be', 'www.primevideo.com', 'yelo.telenet.tv', 'www.proximus.be', 'www.hbomax.com', 'www.vimeo.com', 'www.twitch.tv'], 'Video'))
url_to_cat_map.update(dict.fromkeys(['www.littlebigsnake.com', 'www.catanuniverse.com', 'www.primevideo.com', 'yelo.telenet.tv', 'www.proximus.be', 'www.hbomax.com', 'www.vimeo.com', 'www.twitch.tv'], 'Entertainment & Games'))
url_to_cat_map.update(dict.fromkeys(['www.littlebigsnake.com', 'www.catanuniverse.com', 'www.prosperousuniverse.com', 'www.nl.forgeofempires.com',
                                     'www.agar.io', 'www.play.isleward.com', 'www.linerider.com', 'www.adarkroom.doublespeakgames.com'], 'Entertainment & Games'))
url_to_cat_map.update(dict.fromkeys(['www.spotify.com', 'www.music.apple.com'], 'Music & Audio'))
url_to_cat_map.update(dict.fromkeys(['www.zalando.be', 'www.amazon.nl', 'www.bol.com', 'www.coolblue.be', 'www.collectandgo.be', 'www.delhaize.be',
                                     'www.carrefour.be', 'www.ah.be', 'www.foodbag.be', 'www.hellofresh.be'], 'Shopping'))

#todo problem: vrtnws and vrt have to same url

title_to_cat_map = dict.fromkeys(['vrt nws', 'nieuwsblad', 'hln', 'de morgen', 'de standaard', 'de morgen', ' mo.be', ' knack', 'bbc ', 'the guardian',
                                  'al jazeera', ' cnn', 'fox news', 'humo'], 'News')
title_to_cat_map.update(dict.fromkeys(['facebook'], 'Facebook'))
title_to_cat_map.update(dict.fromkeys(['instagram'], 'Instagram'))
title_to_cat_map.update(dict.fromkeys(['youtube'], 'Youtube'))
title_to_cat_map.update(dict.fromkeys(['twitter'], 'Twitter'))
title_to_cat_map.update(dict.fromkeys(['tiktok'], 'TikTok'))
title_to_cat_map.update(dict.fromkeys(['bereal'], 'BeReal'))
title_to_cat_map.update(dict.fromkeys(['discord'], 'Discord'))
title_to_cat_map.update(dict.fromkeys(['snapchat'], 'Snapchat'))
title_to_cat_map.update(dict.fromkeys(['whatsapp', 'messenger'], 'Messaging'))
title_to_cat_map.update(dict.fromkeys(['reddit', '9gag', 'tumblr', 'blogspot'], 'Forums & Blogs'))
title_to_cat_map.update(dict.fromkeys(['outlook', 'gmail', 'yahoo', 'scarlet'], 'Email'))
title_to_cat_map.update(dict.fromkeys(['zoom', 'google meet', 'google agenda', 'microsoft teams', 'google documenten', 'google spreadsheets',
                                       'google presentaties', 'google formulieren', 'deepl', 'google translate', 'google drive', 'miro',
                                       'Adobe'], 'Work & Productivity'))



def alter_window_info(active_window: dict) -> dict:
    """
    applies changes to active window from aw-watcher-window
    returns: active window without title (non-browser-apps)
             or altered window with title mapped to category (browser-apps)
    """
    # get information from active window
    keys = active_window.keys()
    active_app = active_window.get('app')
    active_title = active_window.get('title')
    # default: no url
    active_url = None
    url = False

    # only safari and chrome based browsers track url
    if 'url' in keys:
        active_url = active_window.get('url')
        url = True

    browsers = ['Chrome', 'Safari', 'Edge', 'Firefox', 'Brave Browser', 'Opera', 'brave.exe', 'chrome.exe',
                'msedge.exe', 'firefox.exe']  # todo: extend list?

    # delete title from non-browser apps (for privacy)
    if active_app not in browsers:
        try:
            active_window.pop('title')
        except KeyError:
            pass

        return active_window

    # Change window title from browser app events
    else:
        altered_title = _change_title(active_title, active_url)
        active_window['title'] = altered_title
        # don't log url
        if url:
            active_window.pop('url')
        altered_window = active_window

        return altered_window


def _change_title(title: str, url=None):
    """
    changes title from active window to category based on keywords in title
    # todo what to do when two keywords are in the title?
    """
    """if url:
        # crazy mapping from url to category
        url = urlparse(url).hostname
        try:
            title = url.replace(url, _map_url(url))
        except AttributeError as ae:
            title = 'excluded',,

    else:"""
    title = _map_title(title)

    return title


def _map_url(url):
    """
    maps url to a custom defined category
    if url not in mapping, return 'excluded'
    """
    if url in url_to_cat_map.keys():
        return url_to_cat_map.get(url)
    else:
        return 'excluded'


def _map_title(title):
    """
    maps title to a custom defined category
    if title not in mapping, return 'Other'
    """

    for key in title_to_cat_map:
        if key in title.lower():
            title = title_to_cat_map.get(key)
            return title
            break
    # default when not tracked
    title = 'excluded'

    return title
