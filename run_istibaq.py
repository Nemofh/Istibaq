import webview
import istibaq_db
import os
import json

class API:
    def add_asset_js(self, data_json):
        data = json.loads(data_json)
        try:
            istibaq_db.add_asset(
                name=data['name'],
                serial_number=data['serial_number'],
                location=data['location'],
                building=data['building'],
                floor=data['floor'],
                status=data['status'],
                next_maintenance=data['next_maintenance']
            )
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_assets_js(self):
        return istibaq_db.get_all_assets()

    def update_asset_js(self, asset_id, data_json):
        data = json.loads(data_json)
        try:
            ok = istibaq_db.update_asset(
                int(asset_id),
                name=data['name'],
                serial_number=data['serial_number'],
                location=data['location'],
                building=data['building'],
                floor=data['floor'],
                status=data['status'],
                next_maintenance=data['next_maintenance']
            )
            return {"status": "success" if ok else "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_asset_js(self, asset_id):
        try:
            ok = istibaq_db.delete_asset(int(asset_id))
            return {"status": "success" if ok else "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def predict_status_js(self, data_json):
        data = json.loads(data_json)
        try:
            result = istibaq_db.predict_asset_status(
                name=data.get("name", ""),
                next_maintenance=data.get("next_maintenance"),
                current_status=data.get("current_status")
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_notifications_js(self):
        return istibaq_db.get_unread_notifications()
    

    def get_sensor_readings_js(self):
        return istibaq_db.get_sensor_readings()

    def simulate_sensor_readings_js(self):
        try:
            readings = istibaq_db.simulate_sensor_readings()
            return {"status": "success", "data": readings}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        

    def get_home_assets_js(self):
        try:
            return istibaq_db.get_home_assets()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_home_assets_js(self, query):
        try:
            return istibaq_db.search_home_assets(query)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def classify_request_js(self, data_json):
        data = json.loads(data_json)
        try:
            result = istibaq_db.classify_maintenance_request(
                asset_name=data.get("asset_name", ""),
                asset_type=data.get("asset_type", ""),
                problem=data.get("problem", "")
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_request_js(self, data_json):
        data = json.loads(data_json)
        try:
            result = istibaq_db.create_maintenance_request(
                asset_id=int(data["asset_id"]),
                problem=data["problem"],
                category=data["category"],
                confidence=data.get("confidence", ""),
                reasoning=data.get("reasoning", ""),
                team=data.get("team", "")
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_recent_requests_js(self):
        try:
            return istibaq_db.get_recent_maintenance_requests()
        except Exception as e:
            return {"status": "error", "message": str(e)}
      

def start_app():
    istibaq_db.init_db()
    api = API()

    html_path = os.path.abspath("istibaq.html")

    window = webview.create_window(
        'منظومة استباق لإدارة الأصول',
        url=html_path,
        js_api=api,
        width=1200,
        height=800
    )
    webview.start()

if __name__ == "__main__":
    start_app()