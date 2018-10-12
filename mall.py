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

    def get_show_videos(self, link):
        page = self.get_page(link)
        return self.extract_videos(page)

    def extract_shows(self, page):
        result = []

        for item in page.select('.video-card__series figure'):
            result.append({
                'label': item.find('h4').text,
                'path': self.url_for('show', link=item.find('a')['href']),
                'thumbnail': item.find('a', attrs={'data-src': True})['data-src']
            })

        return result

    def extract_videos(self, page):
        result = []
        grid = page.find('section', {'class': ['video-grid', 'isVideo']})

        for card in grid.find_all('div', {'class': 'video-card'}):
            link = card.select('.video-card__details a.video-card__details-link')[0]

            result.append({
                'label': link.text,
                'thumbnail': card.find('div', {'class': ['video-card__thumbnail', 'lazy']})['data-src'],
                'path': self.url_for('video', link=link['href']),
                'info': {
                    'duration': self.get_duration(card.find('span', {'class': 'badge__wrapper-video-duration'}).text)
                },
                'is_playable': True
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
        main_link = page.find('source')['src'] + '.m3u8'

        index_list = requests.get(main_link).text

        qualities = re.findall(r'(\d+)/index.m3u8', index_list, flags=re.MULTILINE)
        qualities = reversed(sorted(map(int, qualities)))
        max_quality = int(self.plugin.get_setting('max_quality'))
        selected = filter(lambda x: x <= max_quality, qualities)[0]

        return '%s/%s/index.m3u8' % (main_link.replace('/index.m3u8', ''), selected)