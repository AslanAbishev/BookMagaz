from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def load_home(self):
        self.client.get("/")

    @task
    def load_search(self):
        self.client.get("/api/search?q=python")

    @task
    def load_recommend(self):
        self.client.get("/api/recommend/1")
