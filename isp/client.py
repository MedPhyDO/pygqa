# -*- coding: utf-8 -*-
'''

Nur zu testzwecken bis ein einspungpunkt für Clientabfragen implementiert wurde

Aufrufe wie im entspechendem javascript Modul

siehe auch:

* https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/fetch


CHANGELOG
=========

0.1.1 / 2021-04-27
------------------
- using the same api calls on server

0.1.0 / 2021-01-16
------------------
- First Release


'''

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.1"
__status__ = "Prototype"

from app import run
import json

from isp.config import dict_merge

from flask import current_app

class ispClient(  ):

    def A__init__(self, schema:str=""):

        self.webapp = run( {
            "server" : {
                 "webserver" : {
                     "name" : "test_client",
                     "port" : 5001,
                     "TESTING": True,
                     "reloader" : False
                 }
            }
        })
        self.app = self.webapp.app
        self.schema = schema

        self.init = {
            "headers": {'Content-Type': 'application/json'}
        }

    def __init__(self, schema:str=""):
        '''
        Dies geht nicht lokal sondern nur bei gestarteten server

        # with current_app.test_client() as client:
        #    response = client.get('api/dbtests/', query_string={} )
        self.app = self.webapp.app
        '''
        # print("current",  current_app )
        # self.app = l(schema)

        self.app = current_app.test_client()

        self.schema = schema

        self.init = {
            "headers": {'Content-Type': 'application/json'}
        }


    def renderQueryParams(self, params:dict={}, init:dict={}):
        # limit und offset
        pass

    def sendRequest(self, resource:str="", data:dict={}, init:dict={}):

        _init = dict_merge( {"method": "GET"}, init )

        if _init["method"] == "POST":
            response = self.app.post(
                resource,
                headers=_init["headers"],
                data =json.dumps( data ),
                follow_redirects=True
            )

        elif _init["method"] == "PATCH":

            response = self.app.patch(
                resource,
                headers=_init["headers"],
                data=json.dumps( data ),
                follow_redirects=True
            )

        elif _init["method"] == "DELETE":
            response = self.app.delete(
                resource,
                headers=_init["headers"],
                follow_redirects=True
            )

        else:
            response = self.app.get(
                resource,
                headers=_init["headers"],
                query_string=data,
                follow_redirects=True
            )

        return response

    def upsert( self, id:str=None, data:dict={} ):

        _init = self.init;

        resource = "api/{}".format( self.schema )

        if id == None:
            _init["method"] = "POST"
        else:
            _init["method"] = "PATCH"
            data["id"] = id
            resource = "{}/{}".format(resource, id )

        params = { "data" : data };

        return self.sendRequest(resource, params, _init)


    def QUERY( self, resource:str="", data:dict={}, init:dict={}):

        _init = dict_merge( self.init, init )
        _init["method"] = "GET"

        if resource=="":
            resource = self.schema

        resource = "api/{}".format( resource )
        return self.sendRequest( resource, data=data, init=_init )


    def GET(self, id:str="undefined", init:dict={} ):
        '''
        - 200   Request fulfilled, data follows
        - 403	Forbidden
        - 404	Not Found
        '''
        _init = dict_merge( self.init, init )
        _init["method"] = "GET"
        resource = "api/{}/{}".format( self.schema, id )

        return self.sendRequest(resource, init=_init )

    def POST(self, data:dict={} ):
        '''
        - 201	Created
        - 202	Accepted
        - 403	Forbidden
        - 404	Not Found
        - 409	Conflict
        '''
        return self.upsert( None, data);

    def PATCH(self, id:str=None, data:dict={} ):
        '''
        - 200	Accepted
        - 201	Created
        - 204	No Content
        - 403	Forbidden
        - 404	Not Found
        - 409	Conflict
        '''
        return self.upsert(id, data);

    def DELETE(self, id:str="undefined" ):
        _init = dict_merge( self.init, {} )
        _init["method"] = "DELETE"
        resource = "api/{}/{}".format( self.schema, id )
        return self.sendRequest(resource, init=_init);
