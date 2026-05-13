from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.file = open(r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2\000db696-cf54-4385-b10b-6b16fbb3f985.png", "rb")

    @task
    def test_predict(self):
        self.file.seek(0)  # reset con trỏ file
        files = {"file": self.file}
        self.client.post("/api/v1/inference/predict", files=files)