# google_fit.py
import requests
from datetime import datetime

def fetch_google_fit_steps(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    now = int(datetime.utcnow().timestamp() * 1000)
    start = now - (24 * 60 * 60 * 1000)  # 24시간 전

    response = requests.post(
        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
        headers=headers,
        json={
            "aggregateBy": [{
                "dataTypeName": "com.google.step_count.delta",
                "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
            }],
            "bucketByTime": { "durationMillis": 86400000 },
            "startTimeMillis": start,
            "endTimeMillis": now
        }
    )

    data = response.json()
    total_steps = 0
    try:
        for bucket in data["bucket"]:
            for dataset in bucket["dataset"]:
                for point in dataset.get("point", []):
                    total_steps += int(point["value"][0]["intVal"])
    except:
        raise Exception("걸음 수 파싱 실패")

    return total_steps
