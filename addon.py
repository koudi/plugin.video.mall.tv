# -*- coding: utf-8 -*-
from xbmcswift2 import Plugin
from mall import MallApi

plugin = Plugin()
api = MallApi(plugin)

@plugin.route('/category')
def category_index():
    return api.get_categories()

@plugin.route('/category/<link>')
def category(link):
    plugin.set_content('tvshows')
    return api.get_category(link)

@plugin.route('/show')
def show_index():
    plugin.set_content('tvshows')
    return api.get_shows()

@plugin.route('/show/<link>', name='show_first_season', options={'season': '0', 'link': '-'})
@plugin.route('/show/<link>/<season>', options={'season': '0', 'link': '-'})
def show(link, season='0'):
    plugin.set_content('episodes')
    return api.get_show_videos(link, season)

@plugin.route('/video/<link>')
def video(link):
    url = api.get_video_url(link)
    if url:
        plugin.set_resolved_url(url)

@plugin.route('/livestream/<link>')
def livestream(link):
    url = api.get_video_url(link)
    if url:
        plugin.set_resolved_url(url)

@plugin.route('/popular', name='popular_first_page', options={'video_type': 'popular'})
@plugin.route('/popular/<page>', name='popular', options={'video_type': 'popular'})
@plugin.route('/recent', name='recent_first_page',  options={'video_type': 'recent'})
@plugin.route('/recent/<page>', name='recent',  options={'video_type': 'recent'})
def paged_videos(video_type, page='0'):
    page = int(page)
    items = api.get_paged_videos(page, video_type)

    plugin.set_content('episodes')

    items.append({
        'label': plugin.get_string(30011),
        'path': plugin.url_for(video_type, page=str(page + 1))
    })

    return items

@plugin.route('/live')
def live_index():
    return api.get_live_categories()

@plugin.route('/live/<category_id>')
def live(category_id):
    items = api.get_live_category_videos(category_id)

    plugin.set_content('episodes')

    return items

@plugin.route('/')
def index():
    show = {
        'label': plugin.get_string(30002),
        'path': plugin.url_for(show_index)
    }
    category = {
        'label': plugin.get_string(30001),
        'path': plugin.url_for(category_index)
    }
    recent = {
        'label': plugin.get_string(30010),
        'path': plugin.url_for('recent', page='0')
    }
    popular = {
        'label': plugin.get_string(30013),
        'path': plugin.url_for('popular', page='0')
    }
    live = {
        'label': plugin.get_string(30019),
        'path': plugin.url_for(live_index)
    }
    return [show, category, recent, popular, live]

if __name__ == '__main__':
    plugin.run()
