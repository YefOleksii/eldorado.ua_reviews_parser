import requests
from bs4 import BeautifulSoup
import json
import time
import re

main_url = 'https://api.eldorado.ua/v1/mega_menu?conditions=mm.is_active=1&getTree=1&lang=ua'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299',
    'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6,sr;q=0.5',
    'Referer': 'https://www.google.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
}


def parse_categories(url):
    """
    Takes all ids for every category.
    :param url: The home page of eldorado.
    :return: a set of categories id.
    """
    def get_category_id(category, category_arr):
        """
        Recursive function. It takes category_id from every parent-category.
        If we have more categories in a child-category then we'll use this function again.
        :param category:
        :param category_arr:
        :return:
        """
        category_id = int(category['category_id'])
        if category_id not in category_arr:
            category_arr.append(category_id)

        if 'children' in category:
            for child in category['children']:
                get_category_id(child, category_arr)

    category_arr = list()

    response_main = requests.get(url, headers=HEADERS)
    data_main = response_main.json()['data']

    for parent_category in data_main:
        get_category_id(parent_category, category_arr)

    return category_arr


def parse_products(categoryId):
    """
    Takes id of needed category. Return list of goods' id.
    :param categoryId:
    :return: list_id
    """
    category_api = f'https://api.eldorado.ua/v1.2/goods_attributes_list?categoryId={categoryId}&lang=ua'
    response_category = requests.get(category_api, headers=HEADERS)
    time.sleep(2.8)
    try:
        list_id = response_category.json()['data']['good_ids']
        list_id = list(map(int, list_id))
    except KeyError:
        return

    return list_id


def parse_reviews(goods_id):
    """
    Gathers reviews from a product.
    :param goods_id: id of the current product.
    :return:
    """
    # The variable "limit" contains the amount of reviews for a product.
    limit = 600
    url = f'https://api.eldorado.ua/v1/comments?goods_id={goods_id}' \
          f'&type=%27r%27&limit={limit}&offset=0&returnCommentsList&lang=ua'
    response = requests.get(url, headers=HEADERS)
    data = response.json()['data']

    """If you do not need empty files then just un-comment the next two lines."""
    #if len(data) == 0:
        #return

    formate_json(data, goods_id)


def formate_json(obj, product_id=0):
    """
    Formats json-object and create file in "/reviews/{product_name}".
    :param obj: json-object
    :param product_id: It's "goods_id" of the product. This param is necessary if there are no comments for a product.
    :return:
    """

    def create_file(file_name, file_data):
        """
        Creates .json-file in "/reviews".
        :param file_name:
        :param file_data:
        :return:
        """
        with open(f"reviews/{file_name}.json", 'w', encoding='utf-8') as f:
            json.dump({"reviews": file_data}, f, ensure_ascii=False, indent=4)

    blocked_sym = r'\\|\/|\:|\*|\?|\"|\<|>|\||\ '
    reviews = []

    # If there are no comments then the function will create empty .json file.
    if len(obj) == 0:
        product_url = parse_name(product_id)[0]
        product_name = parse_name(product_id)[1]
        print(f'There are no reviews for: "{product_name}".')
        product_name = "EMPTY_" + re.sub(blocked_sym, '_', product_name)
        data = {"url": product_url}
        create_file(product_name, data)
        return

    product_url = parse_name(obj[0]['goods_id'])[0]
    product_name = parse_name(obj[0]['goods_id'])[1]
    print(f'{len(obj)} reviews for "{product_name}".')
    product_name = re.sub(blocked_sym, '_', product_name)

    for review in obj:
        author_name = review["user_name_ua"] if review.get("user_name_ua") else None
        grade = int(review["rating"]["rating_value"]) if review.get("rating") else None
        date = review["created_at"] if review.get("created_at") else None
        text = review["comment"] if review.get("comment") else None

        review_data = {
            "author_name": author_name,
            "url": product_url,
            "grade": grade,
            "date": date,
            "text": text
        }
        reviews.append(review_data)

    create_file(product_name, reviews)
    return


def parse_name(goods_id):
    """
    Parses name and url for product by "goods_id".
    :param goods_id:
    :return:
    """
    time.sleep(2.8)
    api_url = f'https://api.eldorado.ua/v1/goods_descriptions/?conditions=goods_id={goods_id}&lang=ua'
    response_api = requests.get(api_url, headers=HEADERS)
    # if response_api != 200:
        # print("This product isn't exists.")

    try:
        product_url = response_api.json()['data']['deep_link']
    except KeyError:
        return "None"

    response = requests.get(product_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')
    name = soup.find('div', itemprop="name").text if soup.find('div', itemprop="name") else "None"
    return product_url, name


if __name__ == '__main__':
    # The main code with parsing reviews.
    categories_id = parse_categories(main_url)
    print(f"The amount of categories: {len(categories_id)}.")

    for category in categories_id[:]:
        list_goods_id = parse_products(category)
        if list_goods_id is None:
            continue
        for good_id in list_goods_id[:3]:           # Remove "3" if you need all products.
            parse_reviews(good_id)
            time.sleep(3)
