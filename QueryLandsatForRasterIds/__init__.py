import logging
import requests
import json
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # name = req.params.get('name')
    # if not name:
    #     try:
    #         req_body = req.get_json()
    #     except ValueError:
    #         pass
    #     else:
    #         name = req_body.get('name')

    # if name:
    #     return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    # else:
    #     return func.HttpResponse(
    #         "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
    #         status_code=200
    #     )

    x = req.params.get('x')
    y = req.params.get('y')

    if x is None or y is None:
        return func.HttpResponse(
            mimetype='application/json',
            body=json.dumps({
                "message": "missing either x or y param",
                "success": False
            }),
            status_code=200
        )

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
        'geometry': geom_filter
    }

    landsat_url = 'https://landsat2.arcgis.com/arcgis/rest/services/Landsat/MS/ImageServer/query'
    landsat_res = requests.get(landsat_url, params=params)
    landsat_json = landsat_res.json()
    raster_ids = []
    for feature in landsat_json['features']:
        raster_ids.append(int(feature['attributes']['OBJECTID']))

    return func.HttpResponse(
        mimetype='application/json',
        body=json.dumps({
            "rasterIds": raster_ids,
            "success": True
        }),
        status_code=200
    )
