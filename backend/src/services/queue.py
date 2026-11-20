import os
import redis
def push(kind,i):
 redis.Redis.from_url(os.environ['REDIS_URL']).rpush(kind,i)
