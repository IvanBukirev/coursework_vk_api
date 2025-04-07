import configparser
import json
from datetime import datetime
from tqdm import tqdm
import requests


class Vk:

    def __init__(self, token, version='5.199'):
        self.params = {
                'access_token': token,
                'v':            version
        }
        self.base_url = 'https://api.vk.com/method/'

    def users_info(self, user_id):
        url = f'{self.base_url}users.get'
        params = {'user_ids': user_id}
        response = requests.get(url, params={**self.params, **params})
        return response.json().get('response', {})

    def get_photos(self, user_id, count=5, album_id='profile'):

        url = f'{self.base_url}photos.get'
        params = {
                'owner_id':    user_id,
                'count':       count,
                'album_id':    album_id,
                'extended':    1,
                'photo_sizes': 1
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        return response.json().get('response', {}).get('items', [])

    def get_url_photo(self, photos):
        result = []
        used_names = {}
        for photo in photos:
            url = next((size['url'] for size in photo['sizes'] if size['type'] == 'w'), None)
            size = 'w'
            if url is None:
                url = max(photo['sizes'], key=lambda x: x['width'])['url']
                size = url.split("=")[-1]
            name = photo['likes']['count']
            if name in used_names:
                name = f"{name}_{datetime.fromtimestamp(photo['date']).strftime('%Y-%m-%d_%H-%M-%S')}"
            used_names[name] = True
            result.append({'url': url, 'file_name': f'{name}.jpg', 'size': size})
        return result


class YD:

    def __init__(self, token):
        self.headers = {
                'Authorization': f'OAuth {token}'
        }
        self.base = 'https://cloud-api.yandex.net/v1/disk/resources/'

    def create_folder(self, folder_name):
        url = f'{self.base}?path={folder_name}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            print(f"Папка {folder_name} уже существует.")
            return True
        elif response.status_code == 404:

            create_response = requests.put(url, headers=self.headers)
            if create_response.status_code == 201:
                print(f"Папка {folder_name} успешно создана.")
                return True
            else:
                print(
                    f"Ошибка при создании папки {folder_name}: {create_response.status_code} - {create_response.text}")
                return False
        else:
            print(f"Ошибка при проверке существования папки {folder_name}: {response.status_code} - {response.text}")
            return False

    def upload_file(self, file_content, file_name, folder_name):
        full_path = f"{folder_name}/{file_name}"
        url = f'{self.base}upload?path={full_path}&overwrite=true'
        print(f"Полный путь к файлу на Яндекс.Диске: {full_path}")
        print(f"URL для загрузки файла {file_name}: {url}")
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(
                    f"Ошибка при получении ссылки для загрузки файла {file_name}: {response.status_code} - {response.text}")
            return False

        upload_url = response.json().get('href')
        if not upload_url:
            print(f"Ссылка для загрузки файла {file_name} не найдена.")
            return False

        try:
            upload_response = requests.put(upload_url, data=file_content)
            if upload_response.status_code == 201:
                print(f"Файл {file_name} успешно загружен в папку {folder_name}.")
                return True
            else:
                print(f"Ошибка при загрузке файла {file_name}: {upload_response.status_code} - {upload_response.text}")
                return False
        except Exception as e:
            print(f"Ошибка при загрузке файла {file_name} на Яндекс.Диск: {e}")
            return False


class GD:
    pass


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("settings.ini")
    vk_token = config["Token"]["vk_token"]
    yd_token = config["Token"]["yd_token"]
    vk = Vk(vk_token)
    yd = YD(yd_token)
    # user_id = input("Введите ID пользователя VK: ")
    # photo_count = int(input("Введите количество фотографий для резервного копирования (по умолчанию 5): ") or 5 )

    user_id = '612144641'
    photo_count = 42
    user_info = vk.users_info(user_id)
    photos_list = vk.get_photos(user_id, count=photo_count)
    url_photos = vk.get_url_photo(photos_list)

    folder_name = f"{user_info[0]['first_name']}_{user_info[0]['last_name']}_{datetime.now().strftime('%Y-%m-%d')}"
    yd.create_folder(folder_name)
    for photo in tqdm(url_photos, desc="Загрузка фотографий"):
        response = requests.get(photo['url'])
        if response.status_code == 200:
            yd.upload_file(response.content, photo['file_name'], folder_name)

            with open('data.json', 'w') as file:
                json.dump(url_photos, file, ensure_ascii=False, indent=4)
        else:
            print(f"Ошибка при загрузке файла {photo['file_name']}: {response.status_code}")
