import redis
import json

class RedisHandler:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def set_config(self, config):
        self.redis.set('config', json.dumps(config))

    def get_config(self):
        config = self.redis.get('config')
        return json.loads(config) if config else {}

    def set_printers(self, printers):
        self.redis.set('printers', json.dumps(printers))

    def get_printers(self):
        printers = self.redis.get('printers')
        return json.loads(printers) if printers else {}

    def set_printer_status(self, name, status):
        self.redis.hset('printer_status', name, json.dumps(status))

    def get_printer_status(self, name=None):
        if name:
            status = self.redis.hget('printer_status', name)
            return json.loads(status) if status else {}
        else:
            status = self.redis.hgetall('printer_status')
            return {k.decode(): json.loads(v) for k, v in status.items()}

    def set_printer_progress(self, name, progress):
        self.redis.hset('printer_progress', name, json.dumps(progress))

    def get_printer_progress(self, name=None):
        if name:
            progress = self.redis.hget('printer_progress', name)
            return json.loads(progress) if progress else {}
        else:
            progress = self.redis.hgetall('printer_progress')
            return {k.decode(): json.loads(v) for k, v in progress.items()}