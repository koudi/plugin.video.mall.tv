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
    return [show, category]

if __name__ == '__main__':
    plugin.run()