# -*- coding: utf-8 -*-
from kodiswift import Plugin
from mall import MallApi

plugin = Plugin()
api = MallApi(plugin)

@plugin.route('/category')
def category_index():
    return api.get_categories()

@plugin.route('/category/<link>')
def category(link):
    return api.get_category(link)

@plugin.route('/show')
def show_index():
    return api.get_shows()

@plugin.route('/show/<link>')
def show(link):
    return api.get_show_videos(link)

@plugin.route('/video/<link>')
def video(link):
    url = api.get_video_url(link)
    plugin.set_resolved_url(url)

@plugin.route('/popular/<page>', name='popular', options={'video_type': 'popular'})
@plugin.route('/recent/<page>', name='recent',  options={'video_type': 'recent'})
def paged_videos(video_type, page='0'):
    page = int(page)
    items = api.get_paged_videos(page, video_type)

    items.append({
        'label': plugin.get_string(30011),
        'path': plugin.url_for(video_type, page=str(page + 1))
    })

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
    return [show, category, recent, popular]

if __name__ == '__main__':
    plugin.run()