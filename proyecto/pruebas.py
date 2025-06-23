import requests

x = requests.get('https://w3schools.com/?u=4,d=456')
print(x.status_code)
response = requests.get(url, params=parametros)