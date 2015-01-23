#!/usr/bin/env python

import json
import socket, os
import argparse
import tornado.netutil
import tornado.tcpserver
import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.web

import httplib
import logging

API_PREFIX="/v1.16"


class UHTTPConnection(httplib.HTTPConnection):
    
    def __init__(self, path):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.path = path
    
    def connect(self):
        sock = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
        sock.connect(self.path)
        self.sock = sock

class DockerHandler(tornado.web.RequestHandler):
    
    def initialize(self, host):
        self.host = host
    
    def get(self, path):
        if path == os.path.join(API_PREFIX, "containers", "json"):
            self.proxy(path)
        elif path == os.path.join(API_PREFIX, "images", "json"):
            self.proxy(path)
        else:
            logging.error("Unknown request: %s" % (path))
    
    def post(self, path, **kwds):
        if path == os.path.join(API_PREFIX, "containers", "create"):
            req = json.loads(self.request.body)
            new_req = self.filter_run_request(req)
            self.proxy(path, json.dumps(new_req), {"Content-Type" : "application/json"})

    def filter_run_request(self, request):
        logging.info("Filtering run request: %s" % (request))
        #put some logic here\
        return request

    def proxy(self, path, body=None, headers={}):
        conn = UHTTPConnection(self.host)
        if body is None:
            conn.request("GET", path, headers=headers)
        else:
            conn.request("POST", path, body, headers=headers)
        response = conn.getresponse()
        res_text = response.read()
        print res_text
        self.write(res_text)
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="/var/run/docker.sock")
    parser.add_argument("--proxy", default="/tmp/docker-proxy")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    application = tornado.web.Application([
        (r"(.*)", DockerHandler, {'host' : args.host})
    ])
    
    
    s = tornado.netutil.bind_unix_socket(args.proxy)
    server = tornado.httpserver.HTTPServer(application)
    server.add_sockets([s])
    tornado.ioloop.IOLoop.instance().start()

