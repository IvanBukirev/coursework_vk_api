import requests as rq

rq=rq.get('https://api.vk.com')
print(rq.json())