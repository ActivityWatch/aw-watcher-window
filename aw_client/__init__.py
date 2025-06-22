class ActivityWatchClient:
    def __init__(self, *args, **kwargs):
        self.client_name = kwargs.get('client_name', 'aw-client')
        self.client_hostname = 'localhost'
        self.server_address = 'http://localhost:5600'
    def create_bucket(self, *args, **kwargs):
        pass
    def wait_for_start(self):
        pass
    def heartbeat(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
