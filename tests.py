import pytest
import requests
import re
import random
import string
from uuid import uuid4

BASE_URL = "https://qa-internship.avito.com"



def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))


def generate_payload():
    return {
        "sellerID": random.randint(100000, 999999),
        "name": f"Item {generate_random_string()}",
        "price": random.randint(100, 10000),
        "statistics": {
            "likes": random.randint(1, 10),
            "viewCount": random.randint(1, 10),
            "contacts": random.randint(1, 10)
        }
    }


def get_id_from_response(response):
    """
    Парсит нестандартный ответ API (BUG-04 workaround).
    """
    try:
        data = response.json()
        if 'id' in data:
            return data['id']
        if 'status' in data:
            match = re.search(r'([0-9a-fA-F-]{36})', data['status'])
            if match:
                return match.group(1)
        return None
    except Exception:
        return None



@pytest.fixture
def created_item():
    payload = generate_payload()
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)

    if response.status_code != 200:
        pytest.fail(f"Setup failed: {response.text}")

    item_id = get_id_from_response(response)
    if not item_id:
        pytest.fail("Setup failed: Could not extract ID from response")

    seller_id = payload['sellerID']
    yield {"id": item_id, "sellerID": seller_id, "payload": payload}



# TC-01: Создание объявления
@pytest.mark.xfail(reason="BUG-04: Нарушение контракта ответа (возвращается статус вместо объекта)")
def test_create_item_happy_path():
    payload = generate_payload()
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 200
    data = response.json()

    required_fields = ["id", "sellerId", "name", "price"]
    for field in required_fields:
        assert field in data, f"Field {field} missing in response"


# TC-02: Получение объявления по валидному ID
def test_get_item_by_id(created_item):
    item_id = created_item['id']
    response = requests.get(f"{BASE_URL}/api/1/item/{item_id}")
    assert response.status_code == 200
    data = response.json()[0]
    assert data['id'] == item_id


# TC-03: Получение статистики (v1)
def test_get_statistic_v1(created_item):
    item_id = created_item['id']
    response = requests.get(f"{BASE_URL}/api/1/statistic/{item_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# TC-04: Получение объявлений продавца
def test_get_items_by_seller(created_item):
    seller_id = created_item['sellerID']
    response = requests.get(f"{BASE_URL}/api/1/{seller_id}/item")
    assert response.status_code == 200
    ids = [item['id'] for item in response.json()]
    assert created_item['id'] in ids


# TC-05: Проверка формата даты (BUG-01)
@pytest.mark.xfail(reason="BUG-01: Некорректный формат таймзоны (+0300 +0300)")
def test_check_date_format(created_item):
    seller_id = created_item['sellerID']
    response = requests.get(f"{BASE_URL}/api/1/{seller_id}/item")
    created_at = response.json()[-1]['createdAt']
    iso_regex = r"^\d{4}-\d{2}-\d{2}(T| )\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"
    assert re.match(iso_regex, created_at)


# TC-06: Получение статистики (v2)
def test_get_statistic_v2(created_item):
    item_id = created_item['id']
    response = requests.get(f"{BASE_URL}/api/2/statistic/{item_id}")
    assert response.status_code == 200


# TC-07: Удаление объявления (v2)
def test_delete_item_v2():
    payload = generate_payload()
    create_resp = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    item_id = get_id_from_response(create_resp)
    delete_resp = requests.delete(f"{BASE_URL}/api/2/item/{item_id}")
    assert delete_resp.status_code == 200


# TC-08: Создание объявления без тела
def test_create_item_empty_body():
    response = requests.post(f"{BASE_URL}/api/1/item", json={})
    assert response.status_code == 400


# TC-09: Получение по некорректному ID
def test_get_item_invalid_id_format():
    response = requests.get(f"{BASE_URL}/api/1/item/0")
    assert response.status_code in [400, 404]


# TC-10: Статистика несуществующего ID
def test_get_stat_non_existent_uuid():
    response = requests.get(f"{BASE_URL}/api/1/statistic/{uuid4()}")
    assert response.status_code == 404


# TC-11: Схема ошибки (BUG-02)
@pytest.mark.xfail(reason="BUG-02: Поле result - объект вместо строки")
def test_error_schema_v2():
    response = requests.get(f"{BASE_URL}/api/2/statistic/0")
    error_json = response.json()
    assert isinstance(error_json.get('result'), str)


# TC-12: Удаление некорректного ID
def test_delete_invalid_id():
    response = requests.delete(f"{BASE_URL}/api/2/item/0")
    assert response.status_code in [400, 404]


# TC-13: Метод TRACE (BUG-05)
@pytest.mark.xfail(reason="BUG-05: Нет заголовка Allow")
def test_trace_method(created_item):
    item_id = created_item['id']
    response = requests.request("TRACE", f"{BASE_URL}/api/1/item/{item_id}")
    assert response.status_code == 405
    assert "Allow" in response.headers


# TC-18: Накрутка статистики (BUG-03)
@pytest.mark.xfail(reason="BUG-03: Critical Security! API позволяет накручивать лайки")
def test_create_spoofing_stats():
    payload = generate_payload()
    payload["statistics"] = {"likes": 999999, "viewCount": 999999, "contacts": 999999}

    resp = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    item_id = get_id_from_response(resp)

    get_resp = requests.get(f"{BASE_URL}/api/1/item/{item_id}")
    item_data = get_resp.json()[0]

    current_likes = item_data.get('statistics', {}).get('likes', 0)
    assert current_likes != 999999


def test_create_max_int():
    payload = generate_payload()
    payload['price'] = 2147483647
    resp = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert resp.status_code == 200


def test_create_int_overflow():
    payload = generate_payload()
    payload['price'] = 2147483648
    resp = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    if resp.status_code == 200:
        item_id = get_id_from_response(resp)
        price = requests.get(f"{BASE_URL}/api/1/item/{item_id}").json()[0]['price']
        assert price == 2147483648


# TC-24: Пробелы в имени (BUG-06)
@pytest.mark.xfail(reason="BUG-06: Можно создать имя из пробелов")
def test_create_spaces_name():
    payload = generate_payload()
    payload['name'] = "   "
    response = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert response.status_code == 400


def test_create_float_price():
    payload = generate_payload()
    payload['price'] = 100.55
    assert requests.post(f"{BASE_URL}/api/1/item", json=payload).status_code == 400


def test_sql_injection_name():
    payload = generate_payload()
    payload['name'] = "' OR 1=1;--"
    assert requests.post(f"{BASE_URL}/api/1/item", json=payload).status_code != 500


def test_xss_injection_name():
    payload = generate_payload()
    payload['name'] = "<script>alert(1)</script>"
    resp = requests.post(f"{BASE_URL}/api/1/item", json=payload)
    assert resp.status_code in [200, 400]


def test_state_deleted_item(created_item):
    item_id = created_item['id']
    requests.delete(f"{BASE_URL}/api/2/item/{item_id}")
    assert requests.delete(f"{BASE_URL}/api/2/item/{item_id}").status_code == 404
    assert requests.get(f"{BASE_URL}/api/1/item/{item_id}").status_code == 404


def test_create_extra_fields():
    payload = generate_payload()
    payload['extra'] = "field"
    assert requests.post(f"{BASE_URL}/api/1/item", json=payload).status_code == 200
