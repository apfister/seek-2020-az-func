import os
import logging
import requests
import json
import urllib.parse
from arcgis import GIS
import azure.functions as func
import datetime
import time
from .scripts import createProject


def init_authentication(url, user, passw):
    return GIS(url, user, passw)


def query_for_landsat_raster_ids(x, y):

    if x is None or y is None:
        return "missing either x or y param"

    geom_filter = {
        "spatialReference": {
            "latestWkid": 3857,
            "wkid": 102100
        },
        "x": x,
        "y": y
    }

    where_clause = "(1=1) AND category = 1 AND acquisitiondate >= timestamp '2020-09-13 00:00:00' AND acquisitiondate <= timestamp '2020-10-31 23:59:59'"
    out_fields = 'OBJECTID'
    f = 'json'
    return_geometry = False
    geom_type = 'esriGeometryPoint'
    spatial_rel = 'esriSpatialRelIntersects'

    params = {
        'where': where_clause,
        'outFields': out_fields,
        'f': f,
        'returnGeometry': return_geometry,
        'geometryType': geom_type,
        'spatialRel': spatial_rel,
        'geometry': json.dumps(geom_filter)
    }

    landsat_url = 'https://landsat2.arcgis.com/arcgis/rest/services/Landsat/MS/ImageServer/query'
    landsat_res = requests.get(landsat_url, params=params)
    landsat_json = landsat_res.json()
    raster_ids = []
    for feature in landsat_json['features']:
        raster_ids.append(int(feature['attributes']['OBJECTID']))

    return raster_ids


def create_excalibur_project(raster_ids, ts):
    config = {
        "configFileName": "",
        "user": os.environ['GE_USER'],
        "password": os.environ['GE_PASSWORD'],
        "orgshare": False,
        "sharingurl": os.environ['ORG_URL'] + '/sharing/rest'
    }

    sharingUrlFromPaths = 'https://geospatialcenter.bd.esri.com/portal/sharing/rest'

    username = config["user"]
    password = config["password"]
    portalUrl = config["sharingurl"]
    shareWithOrg = config["orgshare"]

    print("orgshare argument: {}".format(config["orgshare"]))
    print("shareWithOrg variable: {}".format(shareWithOrg))

    project_name = f'Excalibur Project {ts}'

    try:
        projectJson = {
            "title": project_name,
            "summary": "A simple project with just a focus image layer",
            "description": "",
            "instructions": "Please Review the area for potential fires",
            "focusImageLayer": {
                "serviceType": "arcgis",
                "serviceUrl": "https://landsat2.arcgis.com/arcgis/rest/services/Landsat/MS/ImageServer",
                "rasterIds": raster_ids,
                "layerNames": []
            },
            "webmapId": "b3acf0e05f79481b8300445cdbb121f8",
            "observationLayers": [
                {
                    "type": "Feature Layer",
                    "itemId": "d7ee4715bb9847d9a32b290429cfabb4"
                }
            ]
        }

        portalUrl = portalUrl or sharingUrlFromPaths

        if not portalUrl:
            raise Exception(
                "Missing portal url. The portal sharing url must be in the --sharingurl argument or in the project config's SHARING_URL property")

        if not username:
            return {
                "message": "unable to get user username from configuration",
                "success": False
            }

        if not password:
            return {
                "message": "unable to get user password from configuration",
                "success": False
            }

        print("Creating project!!!!")
        theCreator = createProject.ProjectCreator(
            username, password, portalUrl, shareWithOrg)
        itemId = theCreator.makeProject(projectJson)

        return_msg = "Project successfully created. Item ID is: {0}".format(
            itemId)

        org_url = os.environ['ORG_URL']
        return {
            "message": return_msg,
            "success": True,
            "projectId": itemId,
            "excaliburItemLink": f'{org_url}/home/item.html?id={itemId}',
            "excaliburProjectLink": f'{org_url}/apps/excalibur/app.html#/canvas/project?id={itemId}'
        }

    except Exception as e:
        # logger.error("Error creating project: {0}".format(e))
        error_msg = "Error creating project: {0}".format(e)
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": error_msg,
                "success": False
            }),
            status_code=200
        )


def create_mission_project(ts):
    gis = init_authentication(
        os.environ["ORG_URL"], os.environ["GE_USER"], os.environ["GE_PASSWORD"])

    token = gis._con.token

    mission_add_url = os.environ["MISSION_ADD_URL"]
    mission_extent = os.environ["MISSION_EXTENT"]
    mission_template_webmap = os.environ["MISSION_TEMPLATE_WEBMAP"]

    project_title = f'Mission Project {ts}'
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

    return {
        "missionProjectLink": f'{org_url}/apps/mission/app.html#missionanalyst/{mission_id}',
        "missionItemLink": f'{org_url}/home/item.html?id={mission_id}'
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    timestamp_file_name = datetime.datetime.now().strftime("%m_%d_%Y_%H_%M_%S")

    if req.get_body() is None:
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": "missing request body",
                "success": False
            }),
            status_code=200
        )

    # initialize gis
    gis = init_authentication('https://www.arcgis.com',
                              os.environ['SERVICE_USER'], os.environ['SERVICE_PASS'])

    # parse the incoming payload from the webhook
    req_body = str(req.get_body())
    raw_body = req_body.replace("b'payload=", "")
    raw_body = raw_body[:-1]
    body_json = json.loads(raw_body)

    # debug
    # logging.info(req_body)
    # logging.info(raw_body)
    # logging.info(body_json)
    # body_json = [{"name": "workforce", "layerId": 0, "orgId": "LG9Yn2oFqZi5PnO5", "serviceName": "VIIRS_Alerts", "lastUpdatedTime": 1604592345156,
    #               "changesUrl": "https%3a%2f%2fservices.arcgis.com%2fLG9Yn2oFqZi5PnO5%2fArcGIS%2frest%2fservices%2fVIIRS_Alerts%2fFeatureServer%2fextractChanges%3fserverGens%3d%5b1023777%2c1023783%5d%26async%3dtrue%26returnUpdates%3dfalse%26returnDeletes%3dfalse%26returnAttachments%3dfalse", "events": ["FeaturesCreated"]}]

    #   secret = req.params.get('secret')
    # if not secret or secret != os.environ['SECRET']:
    #     return func.HttpResponse(
    #         mimetype='application/json',
    #         body=json.dumps({
    #             "message": "missing or incorrect super-duper secret key",
    #             "success": False
    #         }),
    #         status_code=200
    #     )

    item = body_json[0]
    changes_url = urllib.parse.unquote(item['changesUrl'])

    token = gis._con.token
    changes_res = requests.get(f'{changes_url}&f=json&token={token}')
    changes_json = changes_res.json()
    status_url = changes_json['statusUrl']

    status_url = f'{status_url}?token={token}&f=json'
    status_res = requests.get(status_url)
    status_json = status_res.json()
    if status_json['status'] != 'Completed':
        completed = False
        while completed == False:
            time.sleep(2)
            status_res = requests.get(status_url)
            status_json = status_res.json()
            if status_json['status'] == 'Completed':
                completed = True

    result_url = status_json['resultUrl']
    result_url = f'{result_url}?f=json&token={token}'
    result_res = requests.get(result_url)
    result_json = result_res.json()

    edit = result_json['edits'][0]
    feature = edit['features']
    # add = feature['adds'][0]
    add = {
        "geometry": {
            "x": -6393834.698793099,
            "y": -1998152.7725830504
        },
        "attributes": {
            "WPDA_NAME": "FROM REST API ENDPOINT",
            "FRP": 201,
            "CONFIDENCE": "high",
            "DAY_NIGHT": "D",
            "VIIRS_TIMESTAMP": 1604520846826
        }
    }

    x = add['geometry']['x']
    y = add['geometry']['y']

    # landsat_queryurl = 'http://localhost:7071/api/QueryLandsatForRasterIds'
    # raster_ids = requests.get(landsat_queryurl, params=payload)
    raster_ids = query_for_landsat_raster_ids(x, y)
    if raster_ids is None or len(raster_ids) == 0:
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": "no raster ids found. don't wanna query the entire landsat catalog...",
                "success": False
            }),
            status_code=200
        )

    exc_project = create_excalibur_project(raster_ids, timestamp_file_name)
    # mission_project = create_mission_project(timestamp_file_name)

    # email_params = {
    #     'excaliburProjectLink': exc_project['excaliburProjectLink'],
    #     'excaliburItemLink': exc_project['excaliburItemLink'],
    #     'missionProjectLink': mission_project['missionProjectLink'],
    #     'missionItemLink': mission_project['missionItemLink']
    # }

    email_params = {
        'excaliburProjectLink': exc_project['excaliburProjectLink'],
        'excaliburItemLink': exc_project['excaliburItemLink']
    }

    # send_email_res = requests.post(
    #     os.environ['EMAILER_WEBHOOK_URL'], json=email_params)

    send_email_res = requests.post(
        os.environ['INTEGROMAT_URL_EXC'], json=email_params)

    send_email_json = send_email_res.json()

    return func.HttpResponse(
        mimetype='application/json',
        body=json.dumps({
            'message': send_email_json['message']
        }),
        status_code=200
    )
