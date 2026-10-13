"""
The idolaci module, sending actions to ACI servers
"""

def send_aci_action(host: str, port: int, action: str, params: dict[str,str] = {}, *, timeout: int = 3000, retries: int = 3, ssl_params: dict[str,str] = {}) -> str|None:
	"""
	Simple send ACI action, returning the response as a string, or None on error

	#### Parameters
	* host (str): Hostname
	* port (int): Port
	* action (str): Action name
	* params (dict): Action parameters
	* timeout (int): Request timeout, defaulting to 3 seconds
	* retries (int): Number of retries, defaulting to 3 retries
	* ssl_params (dict): SSL connection parameters

	#### Returns
	The response string or None
	"""

class Request:
	"""
	The Request class
	"""

	def __init__(self, action: str, params: dict[str, str] = {}, *, method: str = 'POST', multipart: bool = False) -> None:
		"""
		Create an ACI Request

		#### Parameters
		* action (str): Action name
		* params (dict): Action parameters
		* method (str): HTTP method, defaulting to 'POST'
		* multipart (bool): Set to True to send a multipart/form-data request
		"""

	def __getitem__(self, name: str) -> str:
		"""@public
		Get the value of the specified request parameter

		#### Parameters
		* name (str): Parameter name

		#### Returns
		The parameter value or the empty string
		"""

	def __setitem__(self, name: str, value: str|None) -> None:
		"""@public
		Set the value of the specified request parameter

		#### Parameters
		* name (str): Parameter name
		* value (str): Parameter value or None to remove the parameter
		"""

class Response:
	"""
	The Response class
	"""

	def __init__(self, content_type: str, buffer: str) -> None:
		"""
		Create an ACI Response

		#### Parameters
		* content_type (str): The content-type of the response data
		* buffer (str): The response data
		"""

	def __getitem__(self, path: str) -> str:
		"""@public
		Get the value of the specified response element

		#### Parameters
		* path (str): XML path to the response element

		#### Returns
		The response element value or the empty string
		"""

class Connection:
	"""
	Connection class for connecting to ACI servers
	"""

	def __init__(self, host: str, port: int = 0, *, retries: int = 1, timeout: int = 60000, ssl_params: dict[str,str] = {}) -> None:
		"""
		Configure a connection for sending requests to an ACI server

		### Parameters
		* host (str): Hostname (or 'host:port' if explicit port number is not provided)
		* port (int): Port number
		* retries (int): Number of retries, defaulting to 1 retry
		* timeout (int): Request timeout, defaulting to 60 seconds
		* ssl_params (dict): SSL connection parameters, e.g. {'SSLMethod': 'Negotiate'}
		"""

	def send(self, request: Request) -> Response:
		"""
		Send a request to the ACI server

		#### Parameters
		* request (`Request`): The request to send

		#### Returns
		The response
		"""