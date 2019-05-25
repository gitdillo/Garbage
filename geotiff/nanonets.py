import requests, json
from requests.auth import HTTPBasicAuth

root = "https://app.nanonets.com/api/v2"

def predictImage(authKey, modelId, imageSrc, mock = False):
    url = root + "/ObjectDetection/Model/{0}/LabelFile/".format(modelId)

    if mock == True:
        return mockResult

    data = {
        "file": open(imageSrc, "rb")
    }

    headers = {
        "accept": "multipart/form-data",
        "accept-encoding": "deflate",
    }

    r = requests.post(
        url,
        files   = data,
        headers = headers,
        auth    = HTTPBasicAuth(authKey, '')
    )

    return json.loads(r.content)

mockResult = json.loads("""{
    "message": "Success",
    "result": [
        {
            "message": "Success",
            "input": "DJI_0182_a.jpg",
            "prediction": [
                {
                    "label": "cigarette_butt",
                    "xmin": 35,
                    "ymin": 22,
                    "xmax": 74,
                    "ymax": 58,
                    "score": 0.97708035
                },
                {
                    "label": "cigarette_butt",
                    "xmin": 734,
                    "ymin": 602,
                    "xmax": 774,
                    "ymax": 628,
                    "score": 0.9723737
                },
                {
                    "label": "cigarette_butt",
                    "xmin": 244,
                    "ymin": 397,
                    "xmax": 277,
                    "ymax": 424,
                    "score": 0.90776646
                },
                {
                    "label": "cigarette_butt",
                    "xmin": 176,
                    "ymin": 260,
                    "xmax": 210,
                    "ymax": 277,
                    "score": 0.88749695
                }
            ]
        }
    ]
}""")
