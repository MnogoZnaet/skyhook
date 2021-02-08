import pprint

from .constants import HostPrograms, Ports, ServerCommands
import requests

try:
    import websockets
    import asyncio
except:
    print("failed to import websockets/asyncio")

class Client(object):
    """
    Base client from which all other Clients will inherit
    """
    def __init__(self):
        super(Client, self).__init__()

        self.host_address = "127.0.0.1"
        self.port = 65500

        self.__echo_execution = True
        self.__echo_payload = True

    def set_echo_execution(self, value):
        """
        If set to true, the client will print out the response coming from the server

        :param value: *bool*
        :return: None
        """
        self.__echo_execution = value

    def echo_execution(self):
        """
        Return True or False whether or not responses from the server are printed in the client

        :return: *bool*
        """
        return self.__echo_execution

    def set_echo_payload(self, value):
        """
        If set to true, the client will print the JSON payload it's sending to the server

        :param value: *bool*
        :return:
        """
        self.__echo_payload = value

    def echo_payload(self):
        """
        Return True or False whether or not the JSON payloads sent to the server are printed in the client

        :return:
        """
        return self.__echo_payload

    def is_host_online(self):
        """
        Convenience function to call on the client. "is_online" comes from the core module

        :return: *bool*
        """
        response = self.execute("is_online", {})
        return response.get("Success")


    def execute(self, command, parameters={}):
        """
        Executes a given command for this client. The server will look for this command in the modules it has loaded

        :param command: *string* or *function* The command name or the actual function that you can import from the
        modules module
        :param parameters: *dict* of the parameters (arguments) for the the command. These have to match the argument
        names on the function in the module exactly
        :return: *dict* of the response coming from the server

        From a Skyhook server it looks like:
        {
             'ReturnValue': ['Camera', 'Cube', 'Cube.001', 'Light'],
             'Success': True,
             'Time': '09:43:18'
        }


        From Unreal it looks like this:
        {
            'ReturnValue': ['/Game/Developers/cooldeveloper/Maps/ScatterDemoLevel/ScatterDemoLevelMaster.ScatterDemoLevelMaster',
                            '/Game/Apple/Core/UI/Widgets/WBP_CriticalHealthLevelVignette.WBP_CriticalHealthLevelVignette',
                            '/Game/Apple/Lighting/LUTs/RGBTable16x1_Level_01.RGBTable16x1_Level_01']
        }
        """
        if callable(command):
            command = command.__name__

        url = "http://%s:%s" % (self.host_address, self.port)
        payload = self.__create_payload(command, parameters)
        response = requests.post(url, json=payload).json()

        if self.echo_payload():
            pprint.pprint(payload)

        if self.echo_execution():
            pprint.pprint(response)

        #return response

    def __create_payload(self, command, parameters):
        """
        Constructs the dictionary for the JSON payload that will be sent to the server

        :param command: *string* name of the command
        :param parameters: *dictionary*
        :return: *dictionary*
        """
        payload = {
            "FunctionName": command,
            "Parameters": parameters
        }

        return payload


class BlenderClient(Client):
    """
    Custom client for Blender
    """
    def __init__(self):
        super(BlenderClient, self).__init__()

        self.host_program = HostPrograms.blender
        self.port = Ports.blender


class MayaClient(Client):
    """
    Custom client for Maya
    """
    def __init__(self):
        super(MayaClient, self).__init__()

        self.host_program = HostPrograms.maya
        self.port = Ports.maya


class HoudiniClient(Client):
    """
    Custom client for Houdini
    """
    def __init__(self):
        super(HoudiniClient, self).__init__()

        self.host_program = HostPrograms.houdini
        self.port = Ports.houdini


class UnrealClient(Client):
    """
    Custom client for Unreal. This overwrites most of the basic functionality because we can't run a Skyhook server
    in Unreal, but have to rely on Web Remote Control.

    There is a file called skyhook in /Game/Python/ that holds the SkyHook classes to be used with this client.
    This file has to be loaded by running "import skyhook" in Unreal's Python editor, or imported when the project
    is loaded.

    """
    def __init__(self):
        super(UnrealClient, self).__init__()

        self.host_program = HostPrograms.unreal
        self.__command_object_path = "/Engine/PythonTypes.Default__SkyHookCommands"
        self.__server_command_object_path = "/Engine/PythonTypes.Default__SkyHookServerCommands"
        self.__headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        self.port = Ports.unreal

    def execute(self, command, parameters={}, function=True, property=False):
        """
        Will execute the command so Web Remote Control understands it.

        :param command: *string* command name
        :param parameters: *dict* of the parameters (arguments) for the the command. These have to match the argument
        names on the function in the module exactly
        :param function: *bool* ignore, not used
        :param property: *bool* ignore, not used
        :return: *dict* of the response coming from Web Remote Control
        """
        url = "http://%s:%s/remote/object/call" % (self.host_address, self.port)

        if command in dir(ServerCommands):
            payload = self.__create_payload(command, parameters, self.__server_command_object_path)
            used_object_path = self.__server_command_object_path
        else:
            payload = self.__create_payload(command, parameters, self.__command_object_path)
            used_object_path = self.__command_object_path


        requests.put(url, json=payload, headers=self.__headers).json()
        response = self.__get_response(used_object_path)

        if self.echo_payload():
            pprint.pprint(payload)

        if self.echo_execution():
            pprint.pprint(response)

        return response

    def set_command_object_path(self, path="/Engine/PythonTypes.Default__PythonClassName"):
        """
        Set the object path for commands

        :param path: *string* path. For Python functions, this has to be something like /Engine/PythonTypes.Default__<PythonClassName>
        You need to add the leading 'Default__', this is what Unreal Engine expects
        :return: None
        """
        self.__command_object_path = path

    def command_object_path(self):
        """
        Gets the command object path

        :return: *string* Object path
        """
        return self.__command_object_path

    def __get_response(self, object_path):
        url = "http://%s:%s/remote/object/call" % (self.host_address, self.port)
        payload = self.__create_payload("get_reply", {}, object_path)

        response = requests.put(url, json=payload, headers=self.__headers).json()

        try:
            return_value = eval(response.get("ReturnValue"))
            response = {'ReturnValue': return_value}
        except:
            pass

        return response

    def __create_payload(self, command, parameters, object_path, echo_payload=True):
        payload = {
            "ObjectPath": object_path,
            "FunctionName": command,
            "Parameters": parameters,
            "GenerateTransaction": True
        }

        return payload

# class WebsocketClient(Client):
#     def __init__(self):
#         super(WebsocketClient, self).__init__()
#         self.uri = "ws://%s:%s" % (self.host_address, self.port)
#         print(self.uri)
#
#     def execute(self, command, parameters={}):
#         payload = self.__create_payload(command, parameters)
#         print(payload)
#
#         async def send():
#             async with websockets.connect(self.uri) as websocket:
#                 await websocket.send(payload)
#                 response = await websocket.recv()
#                 return response
#
#         response = asyncio.get_event_loop().run_until_complete(send())
#         return response
#
#     def __create_payload(self, command, parameters):
#         """
#         Constructs the dictionary for the JSON payload that will be sent to the server
#
#         :param command: *string* name of the command
#         :param parameters: *dictionary*
#         :return: *dictionary*
#         """
#         payload = {
#             "FunctionName": command,
#             "Parameters": parameters
#         }
#
#         return payload
