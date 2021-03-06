import json
import hashlib
import requests
from tqdm import tqdm
from time import sleep
from datetime import datetime
from googleapiclient.discovery import build
from oauth2client import file, client, tools
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaInMemoryUpload


def path():
    return f'Backup {datetime.now().strftime("%d.%m.%Y, %H.%M.%S")}'


class VKDownloader:
    def __init__(self, token, user_id, mode, vk_api_v):
        self.token = token
        self.user_id = user_id
        self.mode = mode
        self.vk_api_v = vk_api_v

    def download(self):
        method = ''
        params = {}

        if self.mode == 'user':
            method = 'photos.get'
            params = {'user_id': f'{self.user_id}', 'album_id': 'profile', 'extended': '1',
                      'access_token': f'{self.token}', 'v': self.vk_api_v}

        elif self.mode == 'all':
            method = 'photos.getAll'
            params = {'owner_id': f'{self.user_id}', 'count': '200', 'extended': '1',
                      'access_token': f'{self.token}', 'v': self.vk_api_v}
        else:
            print('Режим введён неверно!')

        url = f'https://api.vk.com/method/{method}'
        resp = requests.get(url, params).json()

        pics = {}
        for pic in resp['response']['items']:

            sizes = pic.get('sizes')
            max_pic = sorted(sizes, key=lambda k: k['height'], reverse=True)[0]
            pic_size = max_pic.get('height')
            pic_url = max_pic.get('url')

            pic_likes = pic['likes']['count']
            pic_date = datetime.fromtimestamp(pic['date']).strftime('%d.%m.%Y, %H.%M.%S')

            if f'pic_{pic_likes}.jpg' not in pics.keys():
                pics[f'pic_{pic_likes}.jpg'] = {'url': pic_url, 'size': pic_size}
            else:
                pics[f'pic_{pic_likes}_{pic_date}.jpg'] = {'url': pic_url, 'size': pic_size}

        return pics


class OKDownloader:
    def __init__(self, app_key, token, sec_key, user_id, mode):
        self.url = 'https://api.ok.ru/fb.do?'
        self.app_key = app_key
        self.token = token
        self.sec_key = sec_key
        self.user_id = user_id
        self.mode = mode

    def get_albums_ids(self, fid):
        hash_str = f'application_key={self.app_key}count=100fid={fid}method=photos.getAlbums{self.sec_key}'
        sig = hashlib.md5(hash_str.encode()).hexdigest()

        request = f'{self.url}application_key={self.app_key}&fid={fid}&method=photos.getAlbums&count=100' \
                  f'&sig={sig}&access_token={self.token}'

        albums_ids = []
        for album in requests.get(request).json()['albums']:
            albums_ids.append(album['aid'])

        return albums_ids

    def get_album_pics(self, aid):
        hash_str = f'aid={aid}application_key={self.app_key}count=100' \
                   f'fields=photo.PIC_MAX,photo.LIKE_COUNT,photo.CREATED_MSmethod=photos.getPhotos{self.sec_key}'
        sig = hashlib.md5(hash_str.encode()).hexdigest()

        request = f'{self.url}aid={aid}&application_key={self.app_key}&method=photos.getPhotos&count=100' \
                  f'&fields=photo.PIC_MAX%2Cphoto.LIKE_COUNT%2Cphoto.CREATED_MS' \
                  f'&sig={sig}&access_token={self.token}'

        return requests.get(request).json()

    def get_user_pics(self):
        hash_str = f'application_key={self.app_key}count=100' \
                   f'fields=photo.PIC_MAX,photo.LIKE_COUNT,photo.CREATED_MSmethod=photos.getPhotos{self.sec_key}'
        sig = hashlib.md5(hash_str.encode()).hexdigest()

        request = f'{self.url}application_key={self.app_key}&method=photos.getPhotos&count=100' \
                  f'&fields=photo.PIC_MAX%2Cphoto.LIKE_COUNT%2Cphoto.CREATED_MS' \
                  f'&sig={sig}&access_token={self.token}'

        return requests.get(request).json()

    def download(self):

        def user_pics():
            pics = {}
            for user_pic in self.get_user_pics()['photos']:
                pic_likes = user_pic['like_count']
                pic_date = datetime.fromtimestamp(int(str(user_pic['created_ms'])[0:10])).strftime('%d.%m.%Y, %H.%M.%S')

                if f'pic_{pic_likes}.jpg' not in pics.keys():
                    pics[f'pic_{pic_likes}.jpg'] = {'url': user_pic['pic_max'], 'size': 'max'}
                else:
                    pics[f'pic_{pic_likes}_{pic_date}.jpg'] = {'url': user_pic['pic_max'], 'size': 'max'}

            return pics

        def all_pics():
            pics = user_pics()
            for album in self.get_albums_ids(self.user_id):
                for pic in self.get_album_pics(album)['photos']:

                    pic_likes = pic['like_count']
                    pic_date = datetime.fromtimestamp(int(str(pic['created_ms'])[0:10])).strftime('%d.%m.%Y, %H.%M.%S')

                    if f'pic_{pic_likes}.jpg' not in pics.keys():
                        pics[f'pic_{pic_likes}.jpg'] = {'url': pic['pic_max'], 'size': 'max'}
                    else:
                        pics[f'pic_{pic_likes}_{pic_date}.jpg'] = {'url': pic['pic_max'], 'size': 'max'}

            return pics

        if self.mode == 'user':
            return user_pics()
        elif self.mode == 'all':
            return all_pics()
        else:
            print('Режим введён неверно!')


class INSTDownloader:
    def __init__(self, token):
        self.token = token

    def download(self):
        url = 'https://graph.instagram.com/me/media?'
        fields = 'id, media_type, media_url, timestamp'
        params = {'fields': f'{fields}', 'access_token': f'{self.token}'}
        resp = requests.get(url, params).json()

        pics = {}
        for pic in resp['data']:
            pic_date = pic['timestamp'][0:19].replace(':', '.')
            pics[f'pic_{pic_date}.jpg'] = {'url': pic['media_url'], 'size': 'max'}

        while 'next' in resp['paging']:
            resp = requests.get(resp['paging']['next']).json()
            for pic in resp['data']:
                pic_date = pic['timestamp'][0:19].replace(':', '.')
                pics[f'pic_{pic_date}.jpg'] = {'url': pic['media_url'], 'size': 'max'}

        return pics


class YaUploader:
    def __init__(self, token):
        self.token = token

    def upload(self, items):
        path_name = path()
        path_put_url = f'https://cloud-api.yandex.net/v1/disk/resources?path={path_name}'
        requests.put(path_put_url, headers={'Authorization': self.token})

        result_list = []
        with tqdm(desc='Копирование', total=len(items)) as pbar:
            for name, item in items.items():
                item_get_url = f'https://cloud-api.yandex.net/v1/disk/resources/upload?path={path_name}%2F{name}'
                item_put_url = requests.get(item_get_url, headers={'Authorization': self.token}).json()['href']
                requests.put(item_put_url, data=requests.get(item['url']))
                result_list.append({'file_name': name, 'size': str(item['size'])})
                sleep(0.1)
                pbar.update(1)

        json_get_url = f'https://cloud-api.yandex.net/v1/disk/resources/upload?path={path_name}%2F{path_name}.json'
        json_put_url = requests.get(json_get_url, headers={'Authorization': self.token}).json()['href']
        requests.put(json_put_url, json.dumps(result_list))
        print('Копирование завершено успешно!')


class GglUploader:
    def __init__(self, cred_file):
        self.cred_file = cred_file

    def get_token(self):
        scopes = 'https://www.googleapis.com/auth/drive'
        store = file.Storage('storage.json')
        creds = store.get()
        if not creds or creds.invalid:
            try:
                flow = client.flow_from_clientsecrets(self.cred_file, scopes)
                tools.run_flow(flow, store)
            except Exception:
                print('Файл авторизации Google не найден!')

    def upload(self, items):
        self.get_token()
        path_name = path()
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_authorized_user_file('storage.json', scopes)
        service = build('drive', 'v3', credentials=credentials)

        folder_metadata = {
            'name': path_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')

        result_list = []
        with tqdm(desc='Копирование', total=len(items)) as pbar:
            for name, item in items.items():
                name = name
                data = requests.get(item['url']).content
                file_metadata = {
                    'name': name,
                    'parents': [folder_id]
                }
                media = MediaInMemoryUpload(data, resumable=True)
                service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                result_list.append({'file_name': name, 'size': str(item['size'])})
                sleep(0.1)
                pbar.update(1)

        name = f'{path_name}.json'
        data = json.dumps(result_list).encode()
        file_metadata = {
                    'name': name,
                    'parents': [folder_id]
                }
        media = MediaInMemoryUpload(data, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print('Копирование завершено успешно!')
