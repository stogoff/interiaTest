"""
A python script that will post offers over webAPI
(https://developer.allegro.pl/documentation/#section/Authentication)
Create an api client class AllegroApiClient with the post methods that Upload an offer
If the post function of the AllegroApiClient gets a success response you have to show
the result with the urlpage where the offer was uploaded.
"""

import requests
import json
import time
import webbrowser
import sys
import paramiko
from google.cloud import firestore, storage

from secret import CLIENT_ID, CLIENT_SECRET

API_URL = "https://api.allegro.pl"
CODE_URL = "https://allegro.pl/auth/oauth/device"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"


class AllegroApiClient:

    def __init__(self, client_id, client_secret, flow="Device"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.offer_id = None
        if flow == "Device":
            # Device flow
            code = self.get_code()
            result = json.loads(code.text)
            print("\n*\nPlease open this address in the browser:" + result['verification_uri_complete'])
            webbrowser.open(result['verification_uri_complete'])
            self.access_token = self.await_for_access_token(int(result['interval']),
                                                            result['device_code'])
            print("access_token = " + self.access_token)
        else:
            self.access_token = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NTAzMjMwNTMsInVzZXJfbmFtZSI6IjU2NTkzNzU5IiwianRpIjoiNDBiMzQ1MzEtNDU2OS00YmI2LTgwNGQtNDIwZGIyYmM2NDJkIiwiY2xpZW50X2lkIjoiYWI2MDU3ODQ0NjE5NDg0N2FkY2UyM2Q3MjA4OWYyODgiLCJzY29wZSI6WyJhbGxlZ3JvOmFwaTpzYWxlOm9mZmVyczp3cml0ZSIsImFsbGVncm86YXBpOnNhbGU6b2ZmZXJzOnJlYWQiXSwiYWxsZWdyb19hcGkiOnRydWV9.cOy5UZdXXPJ_aN9K56-3ztYC6C4dOFFKys-dltMKCE1PrRtGOhc22D0JBRGQMPbut0nXipG83eHLEXfGKGRgQWwSzESReiNN_NDlCI4JafCkZPT0po3Df64K3KqL5b1hMoxKIzaEKoHHYiKlsVxrx_GCKb-j1ulOd4cKsbiJZnohF6IZaTclB1hdXH8BYJ2BlaVDe-670MsP3-UgaEGGW8jyYMgaP80-1YQGMa95iT93YtCSxl4eMpSXwdu281ylt44T-fJhmU2WuvFnJzONTHGBDViiw0tOfd4n3e-IUU8XnVNY7nnmThrX59j4YNiXL4O1YU0tW5aQ1gFaQj0IqQ'

    def get_code(self):
        try:
            data = {'client_id': self.client_id}
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            api_call_response = requests.post(CODE_URL,
                                              auth=(self.client_id, self.client_secret),
                                              headers=headers, data=data, verify=False)
            return api_call_response
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

    def get_access_token(self, device_code):
        try:
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            data = {'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                    'device_code': device_code}
            api_call_response = requests.post(TOKEN_URL,
                                              auth=(self.client_id, self.client_secret),
                                              headers=headers, data=data, verify=False)
            return api_call_response
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

    def await_for_access_token(self, interval, device_code):
        while True:
            time.sleep(interval)
            result_access_token = self.get_access_token(device_code)
            token = json.loads(result_access_token.text)
            if result_access_token.status_code == 400:
                if token['error'] == 'slow_down':
                    interval += interval
                if token['error'] == 'access_denied':
                    break
            else:
                return token['access_token']

    def get_offers(self):
        endpoint = '/sale/offers'
        headers = {'Authorization': f'Bearer {self.access_token}',
                   'Accept': 'application/vnd.allegro.public.v1+json'}
        response = requests.get(url=API_URL + endpoint, headers=headers)
        return response

    def get_category(self, cat_id):

        endpoint = f'/sale/categories/{cat_id}/parameters'
        headers = {'Authorization': f'Bearer {self.access_token}',
                   'Accept': 'application/vnd.allegro.public.v1+json'}
        response = requests.get(url=API_URL + endpoint, headers=headers)
        cat_p_j = json.loads(response.content)
        for param in cat_p_j['parameters']:
            if param['requiredForProduct']:
                print(f"{param['name']} id: {param['id']} is required")
        return response

    def create_offer(self, data_json):
        url = API_URL + '/sale/product-offers'

        headers = {'Authorization': f'Bearer {self.access_token}',
                   'Accept': 'application/vnd.allegro.public.v1+json',
                   'Content-type': 'application/vnd.allegro.public.v1+json',
                   'User-Agent': 'curl/7.77.0'
                   }
        response = requests.post(url, headers=headers,
                                 data=data_json, verify=False)
        pub_status = None
        result_json = None
        if response is not None:
            if response.status_code == 201:  # Created
                pub_status = json.loads(response.content)['publication']['status']
                result_json = json.loads(response.content)
            elif response.status_code == 202:  # Accepted
                status = 202
                url = response.headers['location']
                result = None
                while status == 202:
                    time.sleep(2)
                    headers = {'Authorization': f'Bearer {self.access_token}',
                               'Accept': 'application/vnd.allegro.public.v1+json',
                               'Content-Type': 'application/vnd.allegro.public.v1+json'}
                    result = requests.get(url, headers=headers)
                    status = result.status_code
                result_json = json.loads(result.content)
                pub_status = result_json['publication']['status']

            elif response.status_code == 400:
                print(response.status_code)
                print(response.content)

            if pub_status in ('PROPOSED', 'ACTIVE'):
                print(f"Publication STATUS:{pub_status}")
                self.offer_id = result_json['id']
                offer_url = f"https://allegro.pl/oferta/{self.offer_id}"
                print(f"offer url: {offer_url}")
                webbrowser.open(offer_url)

        else:
            self.offer_id = None
        return response


def main():
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    client = AllegroApiClient(CLIENT_ID, CLIENT_SECRET, flow="Device")
    client.get_category(123441)  # 123434: men's jewelry
    # sftp settings
    host = "gba.ee"
    port = 22
    username = "rs"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username)
    remote_path = "/home/rs/www/gba.ee/img/"
    sftp = ssh.open_sftp()
    # firestore and storage
    db = firestore.Client()
    storage_client = storage.Client()
    bucket = storage_client.get_bucket("sample-e9236.appspot.com")
    coll = db.collection(u'A6f7Y')
    for doc_ref in coll.list_documents():
        doc = doc_ref.get()
        if doc.exists:
            print(f'Document data: {doc.to_dict()}')
            product_properties = doc.to_dict()
            product = json.load(open("product_params.json", "r"))
            product['productSet'][0]['product']['name'] = product_properties['title'].replace('•','-')
            product['productSet'][0]['product']['description'] = product_properties['description']
            new_images = []
            for image_url in product_properties['images']:
                image = image_url.split('/')[-1]
                b_image = bucket.blob(image)
                local_path = f"images/{image}"
                b_image.download_to_filename(local_path)
                sftp.put(local_path, remote_path + image)
                new_images.append(f"https://gba.ee/img/{image}")
            product['productSet'][0]['product']['images'] = new_images
            #product['productSet'][0]['product']['images'] = product_properties['images']
            product['sellingMode'] = { 'price': {}}
            product['sellingMode']['price']['amount'] = product_properties['price']
            product['sellingMode']['price']['currency'] = "PLN"
            product_json = json.dumps(product)
            client.create_offer(product_json)
        else:
            print(u'No such document!')
        break




if __name__ == "__main__":
    main()
