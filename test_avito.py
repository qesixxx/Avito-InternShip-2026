from http.client import responses

import requests
import random
import pytest

BASE_URL= "https://qa-internship.avito.com"

def get_valid_playload():
    seller_id = random.randint(111111, 999999)
    return{
        "sellerID": seller_id,
        "name": "Смартфон Apple Iphone 16 Pro",
        "price": 120000,
        "statistics": {
            "contacts": 11,
            "likes": 32,
            "viewCount": 101
        }
    }

def created_item(playload):
    return requests.post(f"{BASE_URL}/api/1/item", json=playload)

def get_id(response):
    status_text = response.json().get("status","")
    return status_text.split(" - ")[-1] if " - " in status_text else ""

@pytest.fixture
def created_item_id():
    playload = get_valid_playload()
    response = created_item(playload)
    return get_id(response)


#TC-POS-1
def test_create_item_correct_data():
    playload = get_valid_playload()
    response = created_item(playload)
    assert response.status_code == 200, f"Ожидали Статус-Код 200, но получили {response.status_code}"
    assert "Сохранили объявление" in response.json().get("status","")

#TC-POS-2
def test_get_item_by_id(created_item_id):
    response = requests.get(f"{BASE_URL}/api/1/item/{created_item_id}")
    assert response.status_code == 200, f"Ожидали Статус-Код 200, но получили {response.status_code}"

    data = response.json()
    item = data[0] if isinstance(data, list) else data
    assert item["id"] == created_item_id

#TC-POS-3
def test_get_items_by_seller_id():
    playload = get_valid_playload()
    seller_id = playload["sellerID"]

    create_response = created_item(playload)
    assert create_response.status_code == 200, "Ошибка создания объявления"

    response = requests.get(f"{BASE_URL}/api/1/{seller_id}/item")
    assert response.status_code == 200, f"Ошибка: {response.status_code}"

    data = response.json()
    assert isinstance(data,list), "Ожидался список"
    assert len(data) > 0, "Список пользователя пуст"

    item = data[0]
    expected_fields = ["createdAt", "id", "sellerId", "name", "price", "statistics"]
    for field in expected_fields:
        assert field in item, f"Поле {field} отсутствует у товара"

#TC-POS-4
def test_get_statistics_item_id(created_item_id):
    response = requests.get(f"{BASE_URL}/api/1/statistic/{created_item_id}")
    assert response.status_code == 200, f"Не удалось получить статистику. Код: {response.status_code}"

    data=response.json()
    stats = data[0] if isinstance(data, list) else data
    expected_fields = ["contacts","likes","viewCount"]
    for field in expected_fields:
        assert field in stats, f"В статистике отсутствует поле:{field}"
        assert isinstance(stats[field],int), f"Поле {field} должно быть числом (int), а получили {type(stats[field])}"

#TC-POS-5
def test_delete_item_by_id(created_item_id):
    delete_url= f"{BASE_URL}/api/2/item/{created_item_id}"
    delete_response = requests.delete(delete_url)
    assert delete_response.status_code == 200, f"Ошибка удаления: {delete_response.status_code}"
    get_response = requests.get(f"{BASE_URL}/api/1/item/{created_item_id}")
    assert get_response.status_code == 404, (
        f"Объявление не удалено. Ожидался статус-код: 404, но получили: {get_response.status_code}"
    )

#TC-POS-6
def test_get_empty_seller_guaranteed():
    target_seller_id=random.randint(111111, 999999)
    initial_response=requests.get(f"{BASE_URL}/api/1/{target_seller_id}/item")
    if initial_response.status_code==200:
        items=initial_response.json()
        if isinstance(items,list) and len(items)>0:
            for item in items:
                item_id = item['id']
                requests.delete(f"{BASE_URL}/api/2/item/{item_id}")
    response = requests.get(f"{BASE_URL}/api/1/{target_seller_id}/item")
    assert response.status_code == 200, f"Ошибка сервера: {response.status_code}"
    data=response.json()
    assert data==[], f"Ошибка! Профиль продавца {target_seller_id} не является пустым"

#TC-NEG-01
def test_create_item_invalid_price_type():
    playload = get_valid_playload()
    playload["price"] = "дорого"
    response = created_item(playload)
    assert response.status_code == 400, (
        f"Ожидали 400 Bad Request, но получили {response.status_code}"
    )

    data = response.json()
    expected_error="не передано тело объявления"
    assert data.get("status") == expected_error, (
        f"Ожидали ошибку: {expected_error}, но пришло {data.get('status')}"
    )

#TC-NEG-02
def test_create_item_without_required_field():
    playload=get_valid_playload()
    if "sellerID" in playload:
        del playload["sellerID"]
    response = created_item(playload)
    assert response.status_code == 400, (
        f"Ожидался ответ сервера 400, текущий ответ {response.status_code}"
    )

#TC-NEG-03
@pytest.mark.xfail(reason="Бизнес-баг: сервер принимает отрицательную цену. BUG-01", strict=True)
def test_create_item_invalid_price():
    playload = get_valid_playload()
    playload["price"] = -1
    response = created_item(playload)
    assert response.status_code == 400, (
        f"BUG: Сервер вернул {response.status_code} вместо 400 Bad Request"
    )

#TC-NEG-04
@pytest.mark.xfail(reason="Баг валидации: сервер принимает строку, состоящую только из пробелов как валидное имя. BUG-02", strict=True)
def test_create_item_whitespace_name():
    playload = get_valid_playload()
    playload["name"] = "     "
    response = created_item(playload)
    assert response.status_code == 400, (
        f"BUG: Сервер принял строку из пробелов! Статус: {response.status_code}"
    )

#TC-NEG-05
@pytest.mark.xfail(reason="Сервер принимает слишком длинное название >100 символов. BUG-03", strict=True)
def test_create_item_too_long_name():
    playload = get_valid_playload()
    playload["name"] = "A" * 101
    response = created_item(playload)
    assert response.status_code == 400, (
        f"BUG: Сервер пропустил название длиной {len(playload['name'])} символов"
    )

#TC-CORN-01
@pytest.mark.xfail(reason="Сервер не принимает 0 в полях статистики, считая их пустыми. BUG-04", strict=True)
def test_create_item_zero_stats():
    playload=get_valid_playload()
    playload["statistics"] = {
        "likes": 0, "viewCount": 0, "contacts":0
    }
    response = created_item(playload)
    assert response.status_code == 200, (
        f"BUG: Сервер вернул {response.status_code}, на валидные нулевые счетчики."
    )

#TC-CORN-02
def test_create_item_only_seller_id():
    playload = {"sellerID": 122222}
    response = requests.post(f"{BASE_URL}/api/1/item", json=playload)
    assert response.status_code == 400, (
        'Нельзя создать объявление без цены и названия'
    )
#TC-CORN-03
def test_create_item_with_emoji():
    playload=get_valid_playload()
    playload["name"]='iPhone 16 Pro Max 📱'

    response = created_item(playload)
    assert response.status_code == 200, f"Сервер не принял эмодзи: {response.status_code}"

    item_id = get_id(response)
    item_data = requests.get(f"{BASE_URL}/api/1/item/{item_id}").json()[0]
    assert item_data['name'] == playload['name'], f"Эмодзи исказились. Получено: {item_data['name']}"

#TC-CORN-04
def test_delete_item_twice(created_item_id):
    item_id=created_item_id

    first_delete = requests.delete(f"{BASE_URL}/api/2/item/{item_id}")
    assert first_delete.status_code == 200, f"Ошибка удаления {item_id}"

    second_delete = requests.delete(f"{BASE_URL}/api/2/item/{item_id}")
    assert second_delete.status_code == 404, (
        f"Ожидался ответ сервера 404, вернул {second_delete.status_code}"
    )

#TC-CORN-05
def test_main_items_creation():
    playload = get_valid_playload()
    created_ids=[]
    for i in range (1,6):
        response = created_item(playload)
        assert response.status_code == 200, (
            f"Сервер выдал ошибку на запросе № {i}: {response.status_code}"
        )
        item_id = get_id(response)
        created_ids.append(item_id)

    for clean_id in created_ids:
        requests.delete(f"{BASE_URL}/api/2/item/{clean_id}")

#TC-TIME
def test_create_item_perfomance():
    playload = get_valid_playload()
    response = created_item(playload)
    response_time_ms = response.elapsed.total_seconds()*1000
    assert response.status_code == 200, "Товар не создался, замер некорректен"
    assert response_time_ms < 1000, (
        f"Слишком медленный ответ: {response_time_ms:.2f}ms."
    )

#TC-SECURITY-01
def test_get_items_sql_injection():
    sql_injection_id="' OR 1=1 --"
    response = requests.get(f"{BASE_URL}/api/1/{sql_injection_id}/item")
    assert response.status_code == 400, (
        f"ID айтема не UUID. Сервер вернул {response.status_code} вместо ошибки валидации"
    )

#TC-SECURITY-02
@pytest.mark.xfail(reason="Сервер принимает XSS-скрипты в поле name. BUG-05",strict=True)
def test_create_item_xss_injection():
    playload = get_valid_playload()
    playload["name"] = "<script>alert('xss')</script>"
    response = created_item(playload)
    assert response.status_code == 400, (
        f"BUG: Сервер принял XSS-инъекцию, status: {response.status_code}"
    )

#TC-CONTR
def test_item_contract_validation(created_item_id):
    response = requests.get(f"{BASE_URL}/api/1/item/{created_item_id}")
    item = response.json()[0]
    expected_structure = {
        "createdAt": str,
        "id": str,
        "sellerId": int,
        "name": str,
        "price": int,
        "statistics": dict
    }

    for field, expected_type in expected_structure.items():
        assert field in item, f"Поле {field} отсутствует"
        assert isinstance(item[field],expected_type), f"Поле {field} имеет неверный тип данных"

#TC-EXTRA-E2E
def test_e2e_item_lifecycle():
    playload = get_valid_playload()
    seller_id=playload['sellerID']

    create_res = created_item(playload)
    assert create_res.status_code == 200, "Ошибка при создании в E2E-Tестировании"
    item_id = get_id(create_res)

    get_res = requests.get(f"{BASE_URL}/api/1/item/{item_id}")
    assert get_res.status_code == 200
    assert get_res.json()[0]['sellerId'] == seller_id

    list_res = requests.get(f"{BASE_URL}/api/1/{seller_id}/item")
    ids_in_list = [item["id"] for item in list_res.json()]
    assert item_id in ids_in_list, "Товар не отобразился в списке продавца"

    requests.delete(f"{BASE_URL}/api/2/item/{item_id}")

    final_list_res = requests.get(f"{BASE_URL}/api/1/{seller_id}/item")
    final_ids = [item['id'] for item in final_list_res.json()] if final_list_res.status_code == 200 else []
    assert item_id not in final_ids, "Товар не исчез из списка после удаления"