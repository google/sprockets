#!/usr/bin/env python
# Copyright 2017 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A WebServer implementation based on websocket."""

import asyncio
import functools
import http
import logging
import os

import gui.web_server
import websockets


class _GuiWebSocketServerProtocol(websockets.server.WebSocketServerProtocol):
  """Handles plain http requests as well as websocket."""

  def __init__(self, websocket_url, index_url, html_url, html_dir,
               ws_handler, ws_server, **kwds):
    super().__init__(ws_handler, ws_server, **kwds)
    self._websocket_url = websocket_url
    self._index_url = index_url
    self._html_url = html_url + '/'
    self._html_dir = html_dir
    logging.debug('websocket_url=%s', self._websocket_url)
    logging.debug('html_url=%s', self._html_url)
    logging.debug('html_dir=%s', self._html_dir)

  @asyncio.coroutine
  def process_request(self, path, request_headers):
    if path == self._websocket_url:
      return None  # Continue websocket handshake.
    if path == self._html_url or path == self._html_url[:-1]:
      return (http.HTTPStatus.PERMANENT_REDIRECT,
              [('Location', self._index_url)], None)
    if path.startswith(self._html_url):
      page = self._LoadPage(path[len(self._html_url):])
      if page:
        return http.HTTPStatus.OK, [], page
    return http.HTTPStatus.NOT_FOUND, [], None

  def _LoadPage(self, path_tail):
    try:
      with open(os.path.join(self._html_dir, path_tail)) as f:
        return f.read().encode()
    except Exception as e:
      logging.debug(e)
      return None


class WebSocketServer(gui.web_server.WebServer):
  """A GUI WebServer implementation based on websocket."""

  def __init__(self):
    self._websocket_server = None
    self._port = None
    self._data_callback = None
    self._error_callback = None

  @asyncio.coroutine
  def _OnConnected(self, websocket, path):
    logging.debug('Websocket is connected: %s, path=%s', str(websocket), path)
    try:
      while True:
        data = yield from websocket.recv()
        logging.log(1, 'Got a data from a websocket: %s', str(websocket))
        logging.log(1, 'data: %s', data)
        self._data_callback(self, websocket, data)
    except Exception as e:
      logging.debug(e)
    finally:
      logging.debug('Websocket is closed: %s', str(websocket))
      self._error_callback(self, websocket, 'closed')

  def Start(self, port, data_callback, error_callback, websocket_url,
            index_url, html_url, html_dir):
    logging.debug('Starting a websocket server on port %d', port)
    self._port = port
    self._data_callback = data_callback
    self._error_callback = error_callback
    self._websocket_server = websockets.serve(
        self._OnConnected, port=self._port,
        create_protocol=functools.partial(_GuiWebSocketServerProtocol,
                                          websocket_url, index_url,
                                          html_url, html_dir))
    # TODO(byungchul): Figure out a better thread model.
    asyncio.get_event_loop().run_until_complete(self._websocket_server)
    asyncio.get_event_loop().run_forever()

  def Stop(self):
    logging.debug('Stopping a websocket server on port %d', self._port)
    asyncio.get_event_loop().stop()

  def Send(self, websocket, data):
    logging.log(1, 'Sending a data to a websocket: %s', str(websocket))
    logging.log(1, 'data: %s', data)
    asyncio.get_event_loop().create_task(websocket.send(data))
