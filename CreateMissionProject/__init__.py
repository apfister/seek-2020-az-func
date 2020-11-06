import os
import logging
import requests
import json
import urllib.parse
from arcgis import GIS
import azure.functions as func
import datetime

import azure.functions as func


def init_authentication(url, user, passw):
    return GIS(url, user, passw)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    timestamp_file_name = datetime.datetime.now().strftime("%m_%d_%Y_%H_%M_%S")

    gis = init_authentication(
        os.environ["ORG_URL"], os.environ["GE_USER"], os.environ["GE_PASSWORD"])

    token = gis._con.token

    mission_add_url = os.environ["MISSION_ADD_URL"]
    mission_extent = os.environ["MISSION_EXTENT"]
    mission_template_webmap = os.environ["MISSION_TEMPLATE_WEBMAP"]

    project_title = f'Mission Project {timestamp_file_name}'
    mission_params = {
        "title": project_title,
        "extent": mission_extent,
        "templateWebMapId": mission_template_webmap,
        "async": False,
        "f": "json",
        "token": token
    }

    mission_add_res = requests.post(mission_add_url, data=mission_params)
    mission_add_json = mission_add_res.json()
    # mission_jobid = mission_add_json['jobId']
    mission_id = mission_add_json['id']

    org_url = os.environ["ORG_URL"]

    email_params = {
        "missionProjectLink": f'{org_url}/apps/mission/app.html#missionanalyst/{mission_id}',
        "missionItemLink": f'{org_url}/home/item.html?id={mission_id}'
    }

    # send_email_res = requests.post(
    #     os.environ['EMAILER_WEBHOOK_URL_MISSION'], json=email_params)

    send_email_res = requests.post(
        os.environ['INTEGROMAT_URL'], json=email_params)

    send_email_json = send_email_res.json()

    return func.HttpResponse(
        mimetype='application/json',
        body=json.dumps({
            'message': send_email_json['message']
        }),
        status_code=200
    )
