import logging.config
import json
import logging
import azure.functions as func
import os
import datetime

from .scripts import createProject


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    args = {
        "configFileName": "",
        "user": os.environ['SERVICE_USER'],
        "password": os.environ['SERVICE_PASS'],
        "orgshare": False,
        "sharingurl": os.environ['ORG_URL'] + '/sharing/rest'
    }

    sharingUrlFromPaths = 'https://geospatialcenter.bd.esri.com/portal/sharing/rest'

    username = args["user"]
    password = args["password"]
    portalUrl = args["sharingurl"]
    shareWithOrg = args["orgshare"]

    print("orgshare argument: {}".format(args["orgshare"]))
    print("shareWithOrg variable: {}".format(shareWithOrg))

    secret = req.params.get('secret')
    if not secret or secret != os.environ['SECRET']:
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": "missing or incorrect super-duper secret key",
                "success": False
            }),
            status_code=200
        )

    project_name = req.params.get('projectName')

    if not project_name:
        try:
            req_body = req.get_json()
        except ValueError:
            project_name = f'Generic Project Name - {str(datetime.datetime.now().timestamp())}'
        else:
            project_name = req_body.get('projectName')

    raster_ids = req.params.get('rasterIds')
    if not raster_ids:
        raster_ids = []
    else:
        raster_ids = [int(i) for i in raster_ids.split(',')]

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
            "webmapId": "b3acf0e05f79481b8300445cdbb121f8"
        }

        portalUrl = portalUrl or sharingUrlFromPaths

        if not portalUrl:
            raise Exception(
                "Missing portal url. The portal sharing url must be in the --sharingurl argument or in the project config's SHARING_URL property")

        if not username:
            return func.HttpResponse(
                mimetype='application/json',
                body=json.dumps({
                    "message": "unable to get user username from configuration",
                    "success": False
                }),
                status_code=200
            )

        if not password:
            return func.HttpResponse(
                mimetype='application/json',
                body=json.dumps({
                    "message": "unable to get user password from configuration",
                    "success": False
                }),
                status_code=200
            )

        print("Creating project!!!!")
        theCreator = createProject.ProjectCreator(
            username, password, portalUrl, shareWithOrg)
        itemId = theCreator.makeProject(projectJson)

        return_msg = "Project successfully created. Item ID is: {0}".format(
            itemId)

        org_url = os.environ['ORG_URL']
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": return_msg,
                "success": True,
                "projectId": itemId,
                "excaliburProjectLink": f'{org_url}/apps/excalibur/app.html#/canvas/project?id={itemId}'
            }),
            status_code=200
        )

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
