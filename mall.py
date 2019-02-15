# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re

class MallApi():

    BASE = 'https://www.mall.tv'

    def __init__(self, plugin):
        self.plugin = plugin

    def warn(self, *args, **kwargs):
        self.plugin.log.warning(*args, **kwargs)

    def url_for(self, *args, **kwargs):
        return self.plugin.url_for(*args, **kwargs)

    def get_page(self, url):
        r = requests.get(self.BASE + url)
        return BeautifulSoup(r.content, 'html.parser')

    def get_categories(self, ):
        result = []

        page = self.get_page('/kategorie')

        category = page.find('section', {'class': 'isCategory'})
        cards = category.find_all('div', {'class': 'video-card'})

        self.warn(self.url_for('category', link='3'))

        for card in cards:
            a = card.find('a')
            result.append({
                'path': self.url_for('category', link=a['href']),
                'thumbnail': a['data-src'],
                'label': card.find('h2').contents[0]
            })

        badges = page.find_all('a', {'class': 'badge-kategory'})
        for badge in badges:
            result.append({
                'path': self.url_for('category', link=badge['href']),
                'label': badge.contents[0]
            })

        return result

    def get_category(self, link):
        page = self.get_page(link)
        return self.extract_shows(page)

    def get_shows(self):
        index = 0
        shows = []

        while True:
            self.warn(index)
            page = self.get_page('/Serie/CategorySortedSeries?categoryId=0&sortType=1&page=' + str(index))

            if not page:
                return shows

            slider_item = page.find('div', {'class': 'video-grid__body'})

            if slider_item:
                count = int(slider_item['slider-total'])

            shows += self.extract_shows(page)

            if len(shows) >= count:
                break

            index += 1

        return shows

    def get_show_videos(self, link, season_id):
        if season_id == '0':
            page = self.get_page(link)
            seasons = self.get_seasons(page)
        else:
            page = self.get_page('/Serie/Season?seasonId={}&sortType=0&page=0'.format(season_id))
            seasons = []

        videos = self.extract_videos(page, search_section=True)

        return seasons + videos

    def get_seasons(self, page):
        result = []
        items = page.select('.mall_categories-list li')

        for item in items[1:-1]:
            for li in item.find_all('li'):
                li.extract()

            result.append({
                'label': item.text,
                'path': self.url_for('show', season=item['data-id'])
            })

        return result

    def get_paged_videos(self, page, video_type):
        result = []

        if video_type == 'recent':
            page = self.get_page('/sekce/nejnovejsi?page={0}'.format(page))
        elif video_type == 'popular':
            page = self.get_page('/sekce/nejsledovanejsi?page={0}'.format(page))

        videos = self.extract_videos(page, search_section=(page == 0))

        for r in videos:
            ctx_url = self.url_for('show', link=r['show_link'])
            r['label'] = '[LIGHT]%s[/LIGHT] | %s' % (r['show_name'], r['label'])
            r['context_menu'] = [(self.plugin.get_string(30014), 'XBMC.Container.Update({}, false)'.format(ctx_url))]

        return videos

    def extract_shows(self, page):
        result = []

        for item in page.select('.video-card__series figure'):
            result.append({
                'label': item.find('h4').text,
                'path': self.url_for('show', link=item.find('a')['href']),
                'thumbnail': item.find('a', attrs={'data-src': True})['data-src'],
                'info': {
                    'mediatype': 'tvshow',
                    'tvshowtitle': item.find('h4').text
                }
            })

        return result

    def extract_videos(self, page, search_section=True):
        result = []

        if search_section:
            grid = page.find('section', {'class': ['video-grid', 'isVideo']})
        else:
            grid = page

        for card in grid.find_all('div', {'class': 'video-card'}):
            link = card.select('.video-card__details a.video-card__details-link')[0]

            duration = card.find('span', {'class': 'badge__wrapper-video-duration'})

            show = card.find('a', {'class': ['video-card__info', 'video-card__info-channel']})
            show_title = show.text
            show_link = show['href']

            if not duration:
                continue

            result.append({
                'label': link.text,
                'thumbnail': card.find('div', {'class': ['video-card__thumbnail', 'lazy']})['data-src'],
                'path': self.url_for('video', link=link['href']),
                'info': {
                    'duration': self.get_duration(duration.text),
                    'mediatype': 'episode',
                    'tvshowtitle': show_title,
                    'title': link.text
                },
                'is_playable': True,
                'show_name': show_title,
                'show_link': show_link
            })

        return result

    def get_duration(self, val):
        count = 0
        coef = [1, 60, 3600]

        for index, part in enumerate(reversed(val.split(':'))):
            count += int(part) * coef[index]

        return count

    def get_video_url(self, link):
        page = self.get_page(link)

        source = page.find('source')

        if not source:
            main_link = page.find('meta', {'itemprop': 'image'})['content'].replace('standart.jpg', 'index.m3u8')
        else:
            main_link = source['src'] + '.m3u8'

        index_list = requests.get(main_link).text

        qualities = re.findall(r'(\d+)/index.m3u8', index_list, flags=re.MULTILINE)
        qualities = reversed(sorted(map(int, qualities)))
        max_quality = int(self.plugin.get_setting('max_quality'))
        selected = filter(lambda x: x <= max_quality, qualities)[0]

        url = '{0}/{1}/index{1}.mp4' if self.plugin.get_setting('format') == 'MP4' else '{0}/{1}/index.m3u8';
        return url.format(main_link.replace('/index.m3u8', ''), selected)
