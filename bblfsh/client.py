import os
import sys

import grpc

from bblfsh.pyuast import decode as uast_decode

from bblfsh.aliases import ParseRequest, DriverStub, ProtocolServiceStub, VersionRequest, SupportedLanguagesRequest

# The following two insertions fix the broken pb import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "gopkg/in/bblfsh/sdk/v1/protocol"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "gopkg/in/bblfsh/sdk/v2/protocol"))
sys.path.insert(0, os.path.dirname(__file__))


class NonUTF8ContentException(Exception):
    pass


class BblfshClient(object):
    """
    Babelfish gRPC client. Currently it is only capable of fetching UASTs.
    """

    def __init__(self, endpoint):
        """
        Initializes a new instance of BblfshClient.

        :param endpoint: The address of the Babelfish server, \
                         for example "0.0.0.0:9432"
        :type endpoint: str
        """
        self._channel = grpc.insecure_channel(endpoint)
        self._stub_v1 = ProtocolServiceStub(self._channel)
        self._stub_v2 = DriverStub(self._channel)

    @staticmethod
    def _check_utf8(text):
        try:
            text.decode("utf-8")
        except UnicodeDecodeError:
            raise NonUTF8ContentException("Content must be UTF-8, ASCII or Base64 encoded")

    @staticmethod
    def _get_contents(contents, filename):
        if contents is None:
            with open(filename, "rb") as fin:
                contents = fin.read()
        BblfshClient._check_utf8(contents)
        return contents

    def parse(self, filename, language=None, contents=None, mode=None, raw=False, timeout=None):
        """
        Queries the Babelfish server and receives the UAST response for the specified
        file.

        :param filename: The path to the file. Can be arbitrary if contents \
                         is not None.
        :param language: The programming language of the file. Refer to \
                         https://doc.bblf.sh/languages.html for the list of \
                         currently supported languages. None means autodetect.
        :param contents: The contents of the file. IF None, it is read from \
                         filename.
        :param mode:     UAST transformation mode.
        :param raw:      Return raw binary UAST without decoding it.
        :param timeout: The request timeout in seconds.
        :type filename: str
        :type language: str
        :type contents: str
        :type timeout: float
        :return: UAST object.
        """

        contents = self._get_contents(contents, filename)
        request = ParseRequest(filename=os.path.basename(filename),
                               content=contents,
                               mode=mode,
                               language=self._scramble_language(language))
        response = self._stub_v2.Parse(request, timeout=timeout)
        """
        TODO: return detected language
        TODO: handle syntax errors
        """
        if raw:
            return response.uast
        ctx = uast_decode(response.uast, format=0)
        return ctx

    def supported_languages(self):
        sup_response = self._stub_v1.SupportedLanguages(SupportedLanguagesRequest())
        return sup_response.languages

    def version(self):
        """
        Queries the Babelfish server for version and runtime information.

        :return: A dictionary with the keys "version" for the semantic version and
                 # "build" for the build timestamp.
        """
        return self._stub_v1.Version(VersionRequest())

    @staticmethod
    def _scramble_language(lang):
        if lang is None:
            return None
        lang = lang.lower()
        lang = lang.replace(" ", "-")
        lang = lang.replace("+", "p")
        lang = lang.replace("#", "sharp")
        return lang
