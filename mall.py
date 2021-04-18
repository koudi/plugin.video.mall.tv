# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urlparse, urlunparse

class MallApi():

    def __init__(self, plugin):
        self.plugin = plugin
        self.is_cz = self.plugin.get_setting('country') == '0'
        self.BASE = 'https://www.mall.tv' if self.is_cz else 'https://sk.mall.tv' 

    def get_img_for(self, img_version, url):
        for pattern in ['/mobile/', '/mobile-a/', '/desktop/']:
            if pattern in url:
                url=url.replace(pattern,'/'+img_version+'/')
                break
        return url

    def get_fanart_url(self, url):
        return self.get_img_for('background', url)

    def get_thumb_url(self, url):
        return self.get_img_for('desktop', url)

    def warn(self, *args, **kwargs):
        self.plugin.log.warning(*args, **kwargs)

    def url_for(self, *args, **kwargs):
        return self.plugin.url_for(*args, **kwargs)

    def get_page(self, url):
        r = requests.get(self.BASE + url, cookies=dict(__selectedLanguage= 'cz' if self.is_cz else 'sk'), headers={'User-Agent': 'AndroidApp; LGE LG-850; 8.0.0'})
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
                'thumbnail': self.get_thumb_url(a['data-src']),
                'label': card.find('h2').contents[0],
                'fanart': self.get_fanart_url(a['data-src'])
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

        for r in videos:
            r.pop('show_link')
            r.pop('show_name')

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
        if video_type == 'recent':
            page = self.get_page(('/sekce/nejnovejsi' if self.is_cz else '/sekcia/najnovsie') +'?page={0}'.format(page))
        elif video_type == 'popular':
            page = self.get_page(('/sekce' if self.is_cz else '/sekcia') + '/trending?page={0}'.format(page))

        videos = self.extract_videos(page, search_section=(page == 0))

        for r in videos:
            ctx_url = self.url_for('show', link=r['show_link'])
            r['label'] = '[LIGHT]%s[/LIGHT] | %s' % (r['show_name'], r['label'])
            r['context_menu'] = [(self.plugin.get_string(30014), 'XBMC.Container.Update({}, false)'.format(ctx_url))]
            r.pop('show_link')
            r.pop('show_name')

        return videos

    def get_live_categories(self):
        page = self.get_page(('/zive' if self.is_cz else '/nazivo'))
        video_grids = page.find_all('section', {'class': ['video-grid', 'isVideo']})

        if not video_grids:
            return []

        # display current streams directly in the root as first items
        result = self.get_live_category_videos(0, page)

        # then the rest of the categories
        for category_id, grid in enumerate(video_grids[1:], 1):
            live_section_title = grid.find('h2', {'class': ['video-grid__title']}).text
            result.append({
                'label': live_section_title,
                'path': self.url_for('live', category_id=str(category_id))
            })

        return result

    def get_live_category_videos(self, category, page=None):
        if not page:
            page = self.get_page(('/zive' if self.is_cz else '/nazivo'))

        videos = self.extract_live(page, category)

        for r in videos:
            r['context_menu'] = [(self.plugin.get_string(30014), 'XBMC.Container.Update({}, false)'.format(r['path']))]
            r.pop('show_link')
            r.pop('show_name')

        return videos

    def extract_shows(self, page):
        result = []

        for item in page.select('.video-card__series figure'):
            img = item.find('a', attrs={'data-src': True})['data-src']
            result.append({
                'label': item.find('h4').text,
                'path': self.url_for('show', link=item.find('a')['href']),
                'thumbnail': self.get_thumb_url(img),
                'fanart': self.get_fanart_url(img),
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
            show_fanart = self.get_fanart_url(card.find('div', {'class': ['d-md-none', 'video-card__small-img']})['data-src'])

            if not duration:
                continue
            
            self.plugin.log.debug(link['href'].encode('utf-8'))

            result.append({
                'label': link.text,
                'thumbnail': self.get_thumb_url(card.find('div', {'class': ['video-card__thumbnail', 'lazy']})['data-src']),
                'path': self.url_for('video', link=link['href'].encode('utf-8')),
#                'link': link['href'],
                'info': {
                    'duration': self.get_duration(duration.text),
                    'mediatype': 'episode',
                    'tvshowtitle': show_title,
                    'title': link.text
                },
                'is_playable': True,
                'show_name': show_title,
                'show_link': show_link,
                'fanart': show_fanart
            })

        return result

    def extract_live(self, page, category):
        result = []

        video_grids = page.find_all('section', {'class': ['video-grid', 'isVideo']})

        category_idx = int(category)
        if category_idx >= len(video_grids):
            return result

        grid = video_grids[category_idx]
        for card in grid.find_all('div', {'class': 'video-card'}):
            link = card.select('.video-card__details a.video-card__details-link')[0]

            show = card.find('a', {'class': ['video-card__info', 'video-card__info-channel']})
            show_title = show.text
            show_link = show['href']
            show_fanart = self.get_fanart_url(card.find('div', {'class': ['d-md-none', 'video-card__small-img']})['data-src'])

            self.plugin.log.debug(link['href'].encode('utf-8'))

            result.append({
                'label': link.text,
                'thumbnail': self.get_thumb_url(card.find('div', {'class': ['video-card__thumbnail', 'lazy']})['data-src']),
#                'link': link['href'],
                'path': self.url_for('livestream', link=link['href'].encode('utf-8')),
                'info': {
                    'duration': '',
                    'mediatype': 'episode',
                    'tvshowtitle': show_title,
                    'title': link.text
                },
                'is_playable': True,
                'show_name': show_title,
                'show_link': show_link,
                'fanart': show_fanart
            })

        return result

    def get_duration(self, val):
        count = 0
        coef = [1, 60, 3600]

        for index, part in enumerate(reversed(val.split(':'))):
            count += int(part) * coef[index]

        return count

    def get_video_main_url(self, page):
        # extracts a video url from a script tag, it's in an internal json structure under VideoSource value
        script_tag = page.find(lambda tag: tag.name == 'script' and (tag.string and 'VideoSource' in tag.string))
        # removes everything before the value of VideoSource including the quote character
        tmp_str = re.sub(r'^.*VideoSource"[\s]*:[\s]*"', '', script_tag.string)
        # removes everything after the value including the quote character
        return re.sub(r'["\s]*,["\s]*.*$', '', tmp_str).strip()

    def get_video_url(self, link):
        page = self.get_page(link)

        source = page.find('source')

        if not source:
            main_link = self.get_video_main_url(page)
        else:
            main_link = source['src']

        if not main_link:
            self.plugin.notify(self.plugin.get_string(30021).encode("utf-8"), delay=7000, image=self.plugin._addon.getAddonInfo('icon'))
            return None

        # non "index.m3u8" playlists contains video-id together with quality id
        video_id=''
        if not main_link.endswith('index'):
            video_id=main_link.split('/')[-1]

        main_link += '.m3u8'
        url_parts = urlparse(main_link, 'https')
        main_link = urlunparse(url_parts)

        index_list = requests.get(main_link).text

        qualities = re.findall(video_id+r'(\d+)/index.m3u8', index_list, flags=re.MULTILINE)
        if not len(qualities):
            self.plugin.notify(self.plugin.get_string(30021).encode("utf-8"), delay=7000, image=self.plugin._addon.getAddonInfo('icon'))
            return None
        qualities = reversed(sorted(map(int, qualities)))
        max_quality = int(self.plugin.get_setting('max_quality'))
        for q in qualities:
            selected = q
            if selected <= max_quality:
                break
        self.plugin.log.debug('Selected quality: '+str(selected))
        if selected > max_quality:
            self.plugin.notify(self.plugin.get_string(30020).encode("utf-8") % (str(max_quality), str(selected)), delay=7000, image=self.plugin._addon.getAddonInfo('icon'))

        # current live streams contain 'live' text in their link and have to be treated differently
        if 'live' not in main_link:
            url = '{0}/{1}/index{1}.mp4' if self.plugin.get_setting('format') == 'MP4' else '{0}/{1}/index.m3u8';
            return url.format(main_link.replace('/index.m3u8', ''), selected)
        else:
            url = '{0}{1}/index.m3u8'
            return url.format(main_link.replace('.m3u8', ''), selected)
