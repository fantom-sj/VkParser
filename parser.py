import json
import os
import re
import threading
import time
import vk_api
import requests

from config import login, password

news_save_count = 0
hash_tags_global = []

filters_slovar = {'боюс': 44, 'еды': 134, 'зовут': 135, 'препарат': 138, 'гуманитар': 175, 'прошу': 197,
                  'инвалид': 206, 'зарплат': 217, 'родил': 230, 'пенс': 244, 'смерть': 253, 'травм': 254,
                  'кредит': 255, 'еда': 258, 'ужас': 278, 'хватает': 301, 'одиноч': 311, 'ребён': 321,
                  'умер': 332, 'счёт': 387, 'дети': 450, 'живу': 475, 'оплат': 518, 'операц': 532, 'ребен': 539,
                  'скольк': 552, 'фонд': 566, 'срочн': 578, 'имя': 596, 'реквиз': 606, 'рожден': 618, 'счет': 622,
                  'покуп': 651, 'рубл': 677, 'внимание': 732, 'пожалуйст': 737, 'нужд': 754, 'лечени': 779,
                  'детей': 798, 'город': 828, 'муж': 856, 'сбер': 907, 'телеф': 930, 'любов': 935, 'сумм': 1007,
                  'сбор': 1049, 'болезн': 1064, 'средст': 1102, 'жен': 1130, 'групп': 1152, 'спасиб': 1238,
                  'долг': 1295, 'труд': 1310, 'здоров': 1407, 'помоч': 1441, 'поддерж': 1795, 'жив': 1814, 'нет': 1876,
                  'добр': 1923, 'карт': 1942, 'финанс': 2026, 'работ': 2094, 'благо': 2538, 'кто': 2633, 'помощь': 2871,
                  'помог': 2907, 'может': 2923, 'помощ': 3949}

# VK-авторизация
vk_session = vk_api.VkApi(login, password)
try:
    vk_session.auth(token_only=True)
except vk_api.AuthError as error_msg:
    print(error_msg)
    exit()
vk = vk_session.get_api()

start_time = time.time()
today = str(time.strftime("%d-%m-%Y %H-%M", time.localtime()))
news_index = 0

array_news_id = []

def link_handler(media_link_row):
    photo_url = ''

    if 'photo' in media_link_row:
        photo_media_row = media_link_row['photo']['sizes']
        desired_photo = max(photo_media_row, key=lambda x: x['height'])
        photo_url = desired_photo['url']

    link = media_link_row['url']
    return photo_url, link


def image_handler(media_image_row, news_index):
    try:
        photo_media_row = media_image_row['sizes']
        # Найти лучшее фото
        desired_photo = max(photo_media_row, key=lambda x: x['height'])
        return desired_photo['url']
    except:
        print("Нет фото в записи с индексом: " + str(news_index))
        return ''


def user_handler(from_id, news_index):
    data = \
        vk.users.get(user_ids=from_id, fields='contacts, country, photo_50, photo_100, photo_200_orig, photo_400_orig')[
            0]
    # print(data)
    first_name = data['first_name']
    last_name = data['last_name']
    photo_50_url = data['photo_50']
    photo_100_url = data['photo_100']
    photo_200_orig = data['photo_200_orig']
    photo_400_orig = data['photo_400_orig']

    try:
        country_title = data['country']['title']
        country_id = data['country']['id']
    except:
        country_title = ''
        country_id = ''

    try:
        mobile_phone = data['mobile_phone']
    except:
        mobile_phone = ''

    try:
        home_phone = data['home_phone']
    except:
        home_phone = ''

    # if photo_50_url != '':
    #     image = requests.get(photo_50_url).content
    #     with open(f'NEWS\\{today}\\{news_index}\\user_photo_50_url_photo.png', 'wb') as file:
    #         file.write(image)
    #
    # if photo_100_url != '':
    #     image = requests.get(photo_100_url).content
    #     with open(f'NEWS\\{today}\\{news_index}\\user_photo_100_url.png', 'wb') as file:
    #         file.write(image)
    #
    # if photo_200_orig != '':
    #     image = requests.get(photo_200_orig).content
    #     with open(f'NEWS\\{today}\\{news_index}\\user_photo_200_url.png', 'wb') as file:
    #         file.write(image)
    #
    # if photo_400_orig != '':
    #     image = requests.get(photo_50_url).content
    #     with open(f'NEWS\\{today}\\{news_index}\\user_photo_400_url.png', 'wb') as file:
    #         file.write(image)

    return {'first_name': first_name, 'last_name': last_name, 'user_photo_50_url': photo_50_url,
            'user_photo_100_url': photo_100_url, 'user_photo_200_url': photo_200_orig,
            'user_photo_400_url': photo_400_orig, 'country_title': country_title,
            'country_id': country_id, 'mobile_phone': mobile_phone, 'home_phone': home_phone}


def group_handler(from_id, news_index):
    return 0


def filtr_text(text):
    text = text.lower()

    filters = ['нужна', 'нуждаюсь', 'плохо', 'денег', 'деньги', 'внимание', 'прошу', 'помощ', 'карта',
               'гуманитар', 'детей', 'дети', 'счёт', 'счет', 'спасиб', 'сколько', 'срочно', 'живу', 'жизнь',
               'умер', 'пожалуйста', 'помогите', 'ребёнок', 'ребенок', 'еды', 'еда', 'реквезиты', 'карты', 'sos']

    stop_filters = ['украин', 'уважаем', 'мо рф', 'войн', 'вакцин', 'художник', 'смерт']
    len_filters = len(filters)

    find = 0
    for pattern in filters:
        mat = re.search(pattern, text)
        if mat != None:
            find += 1

    stop_find = 0
    for stop_pattern in stop_filters:
        mat = re.search(stop_pattern, text)
        if mat != None:
            stop_find += 1
    
    
    procent = 30        #Минимальный процент встречаемости слов из словаря в тексте, 
    res = find / len_filters * 100
    if res >= procent and stop_find == 0:       #при значении 30 и текущем словаре будет искать 9 слов из словаря в посте миниммум
        return True
    else:
        return False


def row_handler(news_row, news_index):
    global news_save_count, hash_tags
    media_types = ['photo', 'album', 'link']

    news_id = str(news_row['id'])
    owner_id = str(news_row['owner_id'])  # идентификатор владельца стены, на которой размещена запись
    from_id = str(news_row['from_id'])  # идентификатор автора записи;
    text = news_row['text']  # время публикации записи в формате unixtime
    date_time = news_row['date']  # текст записи

    filtr = filtr_text(text)
    news_id = owner_id + '_' + news_id
    if (news_id in array_news_id) or (owner_id[0] == '-') or (filtr == False):
        return 0

    os.makedirs(f'NEWS\\{today}\\{news_index}\\', exist_ok=True)
    news_save_count += 1
    array_news_id.append(news_id)

    user_data = {}
    user_data = user_handler(owner_id, news_index)

    photo_url = ''
    if 'attachments' in news_row:
        row_type = news_row['attachments'][0]['type']
        if row_type in media_types:
            media_type = news_row['attachments'][0]['type']
            media_row = news_row['attachments'][0][media_type]
            if media_type == 'link':
                photo_url, link = link_handler(media_row)
            elif media_type == 'photo' or media_type == 'album':
                photo_url = image_handler(media_row, news_index)

    link = 'https://vk.com/wall' + news_id
    user_link = 'https://vk.com/id' + owner_id

    print(f'Запись {news_index}: {link}')
    load_news(news_id, owner_id, from_id, text, date_time, photo_url, link, user_data, news_index)


def load_news(news_id, owner_id, from_id, text, date_time, photo_url, link, user_data, news_index):
    # Загрузка фото
    if photo_url != '':
        image = requests.get(photo_url).content
        with open(f'NEWS\\{today}\\{news_index}\\{news_index}_photo.png', 'wb') as file:
            file.write(image)

    # Загрузка JSON
    with open(f'NEWS\\{today}\\{news_index}\\news.json', 'w', encoding='utf-8') as file:
        if len(user_data) == 0:
            str = json.dumps({'owner_id': owner_id,
                              'from_id': from_id,
                              'text': text,
                              'date_time': date_time,
                              'link': link},
                             indent=4, ensure_ascii=False, )
        else:
            str = json.dumps({'news_id': news_id,
                              'user_id': owner_id,
                              'text': text,
                              'date_time': date_time,
                              'link': link,
                              'first_name': user_data['first_name'],
                              'last_name': user_data['last_name'],
                              'user_photo_50_url': user_data['user_photo_50_url'],
                              'user_photo_100_url': user_data['user_photo_100_url'],
                              'user_photo_200_url': user_data['user_photo_200_url'],
                              'user_photo_400_url': user_data['user_photo_400_url'],
                              'country_title': user_data['country_title'],
                              'country_id': user_data['country_id'],
                              'mobile_phone': user_data['mobile_phone'],
                              'home_phone': user_data['home_phone']},
                             indent=4, ensure_ascii=False, )
        file.write(str)


def main(tag):
    # Инициализация
    global news_save_count, next_from, news_index
    threads_list = []

    # Создание дериктории для контента
    os.makedirs(f'NEWS\\{today}\\', exist_ok=True)

    # Получение постов
    # 1-й запрос:
    data = vk.newsfeed.search(q=tag, extended=True)
    print("Найдено " + str(data['total_count']) + " постов")
    print('Их них доступно ' + str(data['count']) + " постов")

    # print(data)

    next_from_status = True
    povtor = True

    try:
        next_from = data['next_from']
    except:
        next_from_status = False

    while (povtor):
        if (next_from_status == False):
            povtor = False

        for row in data['items']:
            thread = threading.Thread(target=row_handler, args=(row, news_index,))
            thread.start()
            threads_list.append(thread)

            # print(news_index)
            news_index += 1

        data = vk.newsfeed.search(q=tag, extended=1, start_from=next_from)
        try:
            next_from = data['next_from']
        except:
            next_from_status = False

    for thread in threads_list:
        if thread.is_alive():
            thread.join()

    print(hash_tags_global)
    print('Парсинг завершён, было проанализированно ' + str(news_index) + ' записей')
    print('Из них сохранено ' + str(news_save_count) + ' записей\n')


if __name__ == '__main__':
    qs = ['финансовая помощь людям sos', 'помогите кто чем может sos',
            '#помощьлюдям', '#нужнапомощь', '#благотворительность',
            '#помощь_людям', '#нужна_помощь',
            'финансовая помощь людям болезнь нужны деньги сбербанк карта sos',
            'Помогите, срочно нужны деньги sos']

    for q in qs:
        main(q)
