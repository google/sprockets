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

"""A web server to interact with GUI clients via http or websocket."""

import abc


class WebServer(object):
  """An abstract class of web server to interact with GUI clients.

  Underlying implementation can be based on http or websocket, or support
  SSL or not.
  """

  @abc.abstractmethod
  def Start(self, port, data_callback, error_callback, websocket_url,
            index_url, html_url, html_dir):
    """Starts the web server.

    Underlying implementation can be based on http or websocket, or support
    SSL or not.

    Args:
      port: tcp/ssl port for http or websocket.
      data_callback: a function called on incoming data from GUI clients.
          The arguments are (web_server, client_id, data) where
            web_server: this instance.
            client_id: an opaque ID or object for a GUI client for the incoming
                data or request.
            data: an incoming byte stream data from a GUI client.
      error_callback: a function called on any error from GUI clients which
          made the connection to the GUI client is invalid. The arguments are
          (web_server, client_id, error) where
            web_server: this instance.
            client_id: an opaque ID or object for a GUI client for the error.
            error: an error string.
      websocket_url: the absolute URL path of websocket or long-live http
          connection.
      index_url: the absolute URL path of main index.html.
      html_url: the absolute URL path of a directory serving static html or
          javascript resources.
      html_dir: the absolute file path of a directory corresponding to html_url.

    Raises:
      IOError: Cannot start a web server.
    """

  @abc.abstractmethod
  def Stop(self):
    """Stops the web server and closes all connections to GUI clients."""

  @abc.abstractmethod
  def Send(self, client_id, data):
    """Sends a data to a GUI client of |client_id|.

    Args:
      client_id: an opaque ID or object for a GUI client for the outgoing data
          or response. It must be gotten by callback call set by Start().
      data: an outgoing byte stream data to a GUI client.

    Raises:
      IOError: Cannot send data to the GUI client.
    """
