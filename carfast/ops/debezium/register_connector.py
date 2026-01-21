import requests
import json

url = "http://localhost:8083/connectors/"
headers = {"Content-Type": "application/json", "Accept": "application/json"}

payload = {
    "name": "carfast-cloud-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        # --- 填空区 ---
        "database.hostname": "47.94.10.217",  # 云端 IP
        "database.port": "5432",
        "database.user": "jcx",        # 账号
        "database.password": "JCX102326wasd",     # 密码
        "database.dbname": "car",            # 数据库名
        # -------------
        "plugin.name": "pgoutput",
        "topic.prefix": "cdc",
        "slot.name": "debezium_cloud_slot",
        "table.include.list": "car.car_model,car.car_series,car.car_brand",
        "include.unknown.datatypes": "true",
        "database.sslmode": "prefer"
    }
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(f"Status Code: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")