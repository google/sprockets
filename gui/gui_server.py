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

"""GUI server running a web server internally.

A simple example to run GUI server:

import gui

class MyObserver(gui.GuiObserver):
  def OnGetStatus(self, gui_server, client_id):
    status_data = <get status of sprockets>
    gui_server.Send(client_id, status_data)

  def OnStart(self, gui_server, client_id):
    <start sprockets test cases>
    gui_server.Broadcast(client, 'Started')
    gui_server.Send(client, 'Success')

  def OnStop(self, gui_server, client_id):
    <sttop sprockets test cases>
    gui_server.Broadcast(client, 'Stopped')
    gui_server.Send(client, 'Success')

observer = MyObserver()
gui_server = gui.GuiServer(8080, observer)
gui_server.Start()  # current implementation doesn't return from here
                    # until the server stops.
gui_server.Stop()
"""

import abc
import logging
import os

import gui.websocket_server


class GuiObserver(object):
  """Observer interface of GUI server."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def OnGetStatus(self, gui_server, client_id):
    """Called on GET_STATUS requests from GUI clients."""

  @abc.abstractmethod
  def OnStart(self, gui_server, client_id):
    """Called on START requests from GUI clients."""

  @abc.abstractmethod
  def OnStop(self, gui_server, client_id):
    """Called on STOP requests from GUI clients."""


class GuiServer(object):
  """GUI server running a web server internally."""

  # Absolute URL path of Websocket.
  _WEBSOCKET_URL = '/sprockets/ws'

  # Absolute directory URL path of html resources.
  _HTML_DIR_URL = '/sprockets/gui'

  # Absolute URL path of GUI main.html.
  _MAIN_HTML_URL = _HTML_DIR_URL + '/main.html'

  # Absolute directory file path of html resources.
  _HTML_DIR_PATH = os.path.dirname(__file__) + '/html'

  def __init__(self, port, observer):
    """Instantiates a GUI server.

    Args:
      port: tcp/ssl port for internal web server.
      observer: GuiObserver called on requests.
    """
    self._web_server = gui.websocket_server.WebSocketServer()
    self._port = port
    self._observer = observer
    self._clients = set()

  def Start(self):
    """Starts accepting requests from GUI clients."""
    self._web_server.Start(self._port, self._OnData, self._OnError,
                           self._WEBSOCKET_URL, self._MAIN_HTML_URL,
                           self._HTML_DIR_URL, self._HTML_DIR_PATH)

  def Stop(self):
    """Stops accepting requests from GUI clients."""
    self._web_server.Stop()

  def Send(self, client_id, data):
    """Sends data to a GUI client of cliet_id."""
    if client_id in self._clients:
      self._web_server.Send(client_id, data)

  def Broadcast(self, data):
    """Broadcasts data to all GUI clients connected now."""
    for c in self._clients:
      self._web_server.Send(c, data)

  def _OnData(self, _, client_id, data):
    if client_id not in self._clients:
      logging.info('A new GUI client is connected: %s', str(client_id))
      self._clients.add(client_id)
    logging.debug('Data from a GUI client: %s', str(client_id))
    # TODO(byungchul): Handle incoming data and call observer accordingly.
    del data  # unused

  def _OnError(self, _, client_id, error):
    logging.info('A GUI client is closed: %s, error=%s', str(client_id), error)
    self._clients.remove(client_id)
