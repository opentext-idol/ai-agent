# BEGIN COPYRIGHT NOTICE
# Copyright 2026 Open Text.
#
# The only warranties for products and services of Open Text and its affiliates and licensors
# ("Open Text") are as may be set forth in the express warranty statements accompanying such
# products and services. Nothing herein should be construed as constituting an additional warranty.
# Open Text shall not be liable for technical or editorial errors or omissions contained herein.
# The information contained herein is subject to change without notice.
#
# END COPYRIGHT NOTICE

"""
The idolnifi module, used by the ExecuteDocumentPython processor
"""

import _idolnifi as _i
import sys
import os
from io import IOBase, RawIOBase, TextIOBase, TextIOWrapper, text_encoding
from typing import Self, TypeVar, Generic
from enum import Enum
from collections.abc import Callable, Iterator, Generator
from threading import Thread,Condition,Lock



def logError(*args, **kwargs):
    """
    Log an error to the processor log

    <div class="tip" markdown="1">`logError` attempts to determine the executing processor and will forward this call to `Processor.logError`</div>
    """
    _i.logError(*args, **kwargs)
def logWarn(*args, **kwargs):
    """
    Log a warning to the processor log

    <div class="tip" markdown="1">`logWarn` attempts to determine the executing processor and will forward this call to `Processor.logWarn`</div>
    """
    _i.logWarn(*args, **kwargs)
def logInfo(*args, **kwargs):
    """
    Log an informational message to the processor log

    <div class="tip" markdown="1">`logInfo` attempts to determine the executing processor and will forward this call to `Processor.logInfo`</div>
    """
    _i.logInfo(*args, **kwargs)
def logDebug(*args, **kwargs):
    """
    Log a debug message to the processor log

    <div class="tip" markdown="1">`logDebug` attempts to determine the executing processor and will forward this call to `Processor.logDebug`</div>
    """
    _i.logDebug(*args, **kwargs)
def logTrace(*args, **kwargs):
    """
    Log a trace message to the processor log

    <div class="tip" markdown="1">`logTrace` attempts to determine the executing processor and will forward this call to `Processor.logTrace`</div>
    """
    _i.logTrace(*args, **kwargs)

class LogStream(IOBase):
    """
    The LogStream class

    Create a writable stream from a log function with the specified value separator and line ending strings

    ````
    errorLogStream = LogStream(logError)
    errorLogStream.write(errorMessage)
    ````
    """
    __slots__ = ('_logFn', '_sep', '_end')
    def __init__(self, logFn, sep:str=' ', end:str='\n'):
        self._logFn = logFn
        self._sep = sep
        self._end = end
    
    def writable(self):
        """
        The LogStream supports writing
        """
        return True
    
    def write(self, *args):
        """
        Write the arguments to the log stream 
        """
        return self._logFn(*args, sep=self._sep, end=self._end)

    def writelines(self, lines):
        super().writelines(self, lines)

_infoLogStream = LogStream(logInfo, sep='', end='')
_warnLogStream = LogStream(logWarn, sep='', end='')

def executePython(args:list[str], env:dict[str,str]=None, stdout:IOBase=_infoLogStream, stderr:IOBase=_warnLogStream, onexit:Callable[[int], None]=None) -> int|None:
    """
    Execute Python as a sub-process

    <div class="warn" markdown="1">The idolnifi module is unavailable to sub-processes</div>

    #### Parameters
    * args (list): Python command arguments
    * env (dict): Additional environment variables
    * stdout (IOBase): stdout stream
    * stderr (IOBase): stderr stream
    * onexit: function to call on process exit with result code, or wait for exit if None

    #### Returns
    Result code if onexit is not callable
    """
    from subprocess import Popen, PIPE
    psenv = {**(env if isinstance(env, dict) else {}),
            **({e: os.environ[e] for e in ['SystemRoot','HOME','USERPROFILE','HOMEPATH','HOMEDRIVE','USERNAME'] if e in os.environ}),
            **{'PYTHONHOME': sys.prefix}}
    process = Popen([sys.executable] + args, stdout=PIPE, stderr=PIPE, encoding='utf-8', env=psenv)
    def outputstream(pstream, stream):
        while line := pstream.readline():
            stream.write(line)
    stdoutThread = Thread(target=outputstream, args=(process.stdout, stdout), daemon=True)
    stderrThread = Thread(target=outputstream, args=(process.stderr, stderr), daemon=True)
    stdoutThread.start()
    stderrThread.start()
    def processwait():
        process.wait()
        stdoutThread.join()
        stderrThread.join()
        if callable(onexit):
            onexit(process.returncode)
    processThread = Thread(target=processwait, daemon=True)
    processThread.start()
    if not callable(onexit):
        processThread.join()
        return process.returncode

def executePythonToLines(args:list[str], outputLines:list[str], errorLines:list[str]=None) -> int:
    """
    Execute Python as a sub-process, getting the command output to a list of lines

    <div class="warn" markdown="1">The idolnifi module is unavailable to sub-processes</div>
    
    #### Parameters
    * args (list): Python command arguments
    * outputLines (list): List to append stdout/stderr lines to
    * errorLines (list): Optional list to append stderr lines instead of outputLines
    
    #### Returns
    Result code
    """
    def outputAppender(*args, sep='', end=''):
        outputLines.append(''.join(map(str, args)))
    def errorAppender(*args, sep='', end=''):
        errorLines.append(''.join(map(str, args)))
    return executePython(args,
        stdout=LogStream(outputAppender, sep='', end=''),
        stderr=LogStream(outputAppender if errorLines is None else errorAppender, sep='', end=''))

DefaultPackageDirectory:str = next((p for p in sys.path if p.endswith('site-packages')), None)
"""
Default package directory used for package installation
"""

PersistentPackageDirectory:str = 'idol_repository/pypackages'
"""
Package directory (idol_repository/pypackages) that can be used for persistent package installation instead of the default

<div class="tip" markdown="1">The `PersistentPackageDirectory` is only searched after first looking in the `DefaultPackageDirectory` for modules</div>
"""

def getInstalledPackages(*packageDirectories:str) -> dict[str,str]:
    """
    Get a dictionary of the installed packages

    #### Parameters
    * packageDirectories: Package directories to list packages from, defaulting to (`DefaultPackageDirectory`, `PersistentPackageDirectory`)

    #### Returns
    A dictionary of installed package names and versions
    """
    pipArgs = ['-m', 'pip', 'list', '--format', 'freeze']
    if 'PIP_CACHE_DIR' not in os.environ:
        pipArgs.extend(['--no-cache-dir'])
    for dir in ((DefaultPackageDirectory, PersistentPackageDirectory) if len(packageDirectories) == 0 else packageDirectories):
        pipArgs.extend(['--path', dir])
    lines = []
    executePythonToLines(pipArgs, lines, [])
    packages = {}
    for line in lines:
        s = line.strip().split('==')
        if len(s) == 2:
            packages.setdefault(s[0], s[1])
    return packages

def installPackage(*packageNames:str, packageDirectory:str = None, outputLines:list[str] = None, errorLines:list[str]=None, proxy:str = None) -> bool:
    """
    Install packages to the built-in or custom package directory
    
    #### Parameters
    * packageNames: Package names, package names with version constraints, or package URLs
    * packageDirectory (str): Package directory, defaulting to `DefaultPackageDirectory`
    * outputLines (list): Optional list to collect the command output
    * errorLines (list): Optional list to append stderr lines instead of outputLines
    * proxy (str): Optional proxy string to provide to the command
    
    #### Returns
    True if the installation succeeded, False otherwise
    """
    pipArgs = ['-m', 'pip', '-q', '--no-input', '--disable-pip-version-check', 'install']
    packageDir = None
    if packageDirectory is not None and (not os.path.exists(packageDirectory) or os.path.isdir(packageDirectory)):
        packageDir = os.path.abspath(packageDirectory)
        pipArgs.extend(['--target', packageDir])
    else:
        pipArgs.extend(['-U'])
    if proxy is not None:
        pipArgs.extend(['--proxy', proxy])
    if 'PIP_CACHE_DIR' not in os.environ:
        pipArgs.extend(['--no-cache-dir'])
    lines = outputLines if outputLines is not None else []
    result = 0 == executePythonToLines(pipArgs + list(filter(lambda p: not p.startswith('-'), packageNames)), lines, errorLines)
    if result:
        from importlib import invalidate_caches
        invalidate_caches()
    return result

def getStorageDirectory() -> str:
    """
    Get the storage directory for the processor

    This is typically used for persistent configuration files or state

    <div class="tip" markdown="1">`getStorageDirectory` attempts to determine the executing processor and will forward this call to `Processor.getStorageDirectory`</div>

    #### Returns
    The path to the idol_repository storage directory for the processor
    """
    return _i.getStorageDirectory()

def getFilesStorageDirectory() -> str:
    """
    Get the files storage directory for the processor

    This is typically used for temporary files or files linked to a `FlowFileDocument`

    <div class="tip" markdown="1">`getFilesStorageDirectory` attempts to determine the executing processor and will forward this call to `Processor.getFilesStorageDirectory`</div>

    #### Returns
    The path to the idol_repository files storage directory for the processor
    """
    return _i.getFilesStorageDirectory()

def getTempFile(prefix:str = '', extn:str = '.tmp') -> str:
    """
    Get a temporary file name with the given filename prefix and extension

    <div class="tip" markdown="1">`getTempFile` attempts to determine the executing processor and will forward this call to `Processor.getTempFile`</div>

    #### Parameters
    * prefix (str): Filename prefix string
    * extn (str): File extension (default '.tmp')

    #### Returns
    Temporary file path within the directory returned by `getFilesStorageDirectory`
    """
    return _i.getTempFile(prefix, extn)

def getPropertyDescriptor(name:str) -> 'PropertyDescriptor':
    """
    Get the named `PropertyDescriptor`

    <div class="tip" markdown="1">`getPropertyDescriptor` attempts to determine the executing processor and will forward this call to `Processor.getPropertyDescriptor`</div>

    #### Parameters
    * name (str): Property name

    #### Returns
    `PropertyDescriptor` for the named property
    """
    return _i.getPropertyDescriptor(name)

def isScheduled() -> bool:
    """
    <div class="tip" markdown="1">`isScheduled` attempts to determine the executing processor and will forward this call to `Processor.isScheduled`</div>

    #### Returns
    True if the processor is scheduled, False otherwise
    """
    return _i.isScheduled()



class Processor:
    """
    The Processor class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule

    def getId(self) -> str:
        """
        #### Returns
        The ID of the processor
        """
        return _i.Processor_getId(self._c)
    
    def logError(self, *args, **kwargs):
        """Log an error to the processor log"""
        _i.Processor_logError(self._c, *args, **kwargs)

    def logWarn(self, *args, **kwargs):
        """Log a warning to the processor log"""
        _i.Processor_logWarn(self._c, *args, **kwargs)

    def logInfo(self, *args, **kwargs):
        """Log an informational message to the processor log"""
        _i.Processor_logInfo(self._c, *args, **kwargs)

    def logDebug(self, *args, **kwargs):
        """Log a debug message to the processor log"""
        _i.Processor_logDebug(self._c, *args, **kwargs)

    def logTrace(self, *args, **kwargs):
        """Log a trace message to the processor log"""
        _i.Processor_logTrace(self._c, *args, **kwargs)

    def getStorageDirectory(self) -> str:
        """
        Get the storage directory for the processor

        This is typically used for persistent configuration files or state

        #### Returns
        The path to the idol_repository storage directory for the processor
        """
        return _i.Processor_getStorageDirectory(self._c)

    def getFilesStorageDirectory(self) -> str:
        """
        Get the files storage directory for the processor

        This is typically used for temporary files or files linked to a `FlowFileDocument`

        #### Returns
        The path to the idol_repository files storage directory for the processor
        """
        return _i.Processor_getFilesStorageDirectory(self._c)

    def getTempFile(self, prefix:str = '', extn:str = '.tmp') -> str:
        """
        Get a temporary file name with the given filename prefix and extension

        #### Parameters
        * prefix (str): Filename prefix string
        * extn (str): File extension (default '.tmp')

        #### Returns
        Temporary file path within the directory returned by `getFilesStorageDirectory`
        """
        return _i.Processor_getTempFile(self._c, prefix, extn)

    def getPropertyDescriptor(self, name:str) -> 'PropertyDescriptor':
        """
        Get the named `PropertyDescriptor`

        #### Parameters
        * name (str): Property name

        #### Returns
        `PropertyDescriptor` for the named property
        """
        return _i.Processor_getPropertyDescriptor(self._c, name)

    def isScheduled(self) -> bool:
        """
        #### Returns
        True if the processor is scheduled, False otherwise
        """
        return _i.Processor_isScheduled(self._c)



class Scope(Enum):
    """
    Enumeration for the component state storage scope when accessd via the `StateManager`
    """
    CLUSTER = 0
    LOCAL = 1



class StateMap:
    """
    The StateMap class, accessd via the `StateManager`
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def get(self, key:str) -> str:
        """
        Returns the value associated with the given key

        #### Parameters
        * key (str): State lookup key

        #### Returns
        Value associated with the given key
        """
        return _i.StateMap_read(self._c, key)
    
    def getVersion(self) -> int:
        """
        #### Returns
        The version of the state, incremented each time the state is updated
        """
        return _i.StateMap_getVersion(self._c)
    
    def toMap(self) -> dict[str,str]:
        """
        #### Returns
        The dictionary of state keys and values
        """
        return _i.StateMap_toMap(self._c)



class StateManager:
    """
    The StateManager class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def clear(self, scope:Scope):
        """
        Clears all keys and values from the state
        
        #### Parameters
        * scope (`Scope`): The scope to use
        """
        _i.StateManager_clear(self._c, scope.value)
    
    def getState(self, scope:Scope) -> StateMap:
        """
        Returns the current state for the component

        #### Parameters
        * scope (`Scope`): The scope to use

        #### Returns
        The `StateMap`
        """
        return _i.StateManager_getState(self._c, scope.value)
    
    def replace(self, oldState:StateMap, newState:dict, scope:Scope) -> bool:
        """
        Updates the value of the state to the new value if and only if the value currently is the same as the given oldValue

        #### Parameters
        * oldState (`StateMap`): the old value to compare against
        * newState (dict): The value to change the state to if the state matches the oldState
        * scope (`Scope`): The scope to use

        #### Returns
        true if the state was updated to the new value, otherwise false
        """
        return _i.StateManager_replace(self._c, oldState, newState, scope.value)
    
    def setState(self, state:dict, scope:Scope):
        """
        Updates the value of the component state

        #### Parameters
        * state (dict): The value to change the state to
        * scope (`Scope`): The scope to use
        """
        _i.StateManager_setState(self._c, state, scope.value)



class PropertyDescriptor:
    """
    The PropertyDescriptor class

    Equality comparable and hashable by the property name
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def __hash__(self):
        return hash(self.getName())

    def __eq__(self, other):
        return self.getName() == other.getName()

    def getName(self) -> str:
        """
        #### Returns
        The property name
        """
        return _i.PropertyDescriptor_getName(self._c)

    def isDynamic(self) -> bool:
        """
        #### Returns
        True if the property is dynamic, False otherwise
        """
        return _i.PropertyDescriptor_isDynamic(self._c)



class PropertyValue:
    """
    The PropertyValue class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule

    def getValue(self) -> str:
        """
        #### Returns
        The property value as a string
        """
        return _i.PropertyValue_getValue(self._c)

    def evaluateAttributeExpressions(self, flowfile:'FlowFile' = None) -> 'PropertyValue':
        """
        Evaluate attribute expressions
        
        #### Parameters
        * flowfile (`FlowFile`): `FlowFile` to use in expression evaluation
        
        #### Returns
        The resulting `PropertyValue`
        """
        return _i.PropertyValue_evaluateAttributeExpressions(self._c, flowfile)



class ProcessContext:
    """
    The ProcessContext class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def getName(self) -> str:
        """
        #### Returns
        The name of the processor
        """
        return _i.ProcessContext_getName(self._c)
    
    def getProperties(self) -> dict[PropertyDescriptor,str]:
        """
        Get all the properties for the processor
        
        #### Returns
        Dictionary of `PropertyDescriptor` to value string
        """
        return _i.ProcessContext_getProperties(self._c)
    
    def getProperty(self, propertydescriptor:PropertyDescriptor|str) -> PropertyValue:
        """
        Get the current value for the property

        #### Parameters
        * propertydescriptor (`PropertyDescriptor` | str): `PropertyDescriptor` or name

        #### Returns
        `PropertyValue` containing the value of the property
        """
        if isinstance(propertydescriptor, str):
            return _i.ProcessContext_getProperty(self._c, _i.getPropertyDescriptor(propertydescriptor))
        else:
            return _i.ProcessContext_getProperty(self._c, propertydescriptor)
    
    def newPropertyValue(self, value:str) -> PropertyValue:
        """
        Get a `PropertyValue` from a value string

        #### Parameters
        * value (str): Value string
        
        #### Returns
        `PropertyValue` for the value string
        """
        return _i.ProcessContext_newPropertyValue(self._c, value)
    
    def getAnnotationData(self) -> str:
        """
        #### Returns
        The annotation data configured for this processor
        """
        return _i.ProcessContext_getAnnotationData(self._c)
    
    def getMaxConcurrentTasks(self) -> int:
        """
        #### Returns
        The maximum number of threads that this processor may be executing on at any given time
        """
        return _i.ProcessContext_getMaxConcurrentTasks(self._c)
    
    def isConnectedToCluster(self) -> bool:
        """
        #### Returns
        True if this node is connected to a cluster, False otherwise
        """
        return _i.ProcessContext_isConnectedToCluster(self._c)
    
    def getStateManager(self) -> StateManager:
        """
        #### Returns
        The `StateManager` that can be used to store and retrieve state for this component
        """
        return _i.ProcessContext_getStateManager(self._c)
    
    def hasIncomingConnection(self) -> bool:
        """
        #### Returns
        True if the processor has one or more incoming connections, False otherwise
        """
        return _i.ProcessContext_hasIncomingConnection(self._c)
    
    def hasConnection(self, relationship:str) -> bool:
        """
        Returns whether the processor has outbound connections for a relationship name

        #### Parameters
        * relationship (str): The relationship name

        #### Returns
        true if the relationship has one or more outbound connections, false otherwise
        """
        return _i.ProcessContext_hasConnection(self._c, relationship)
    
    def yieldProcessor(self):
        """
        Causes the Processor not to be scheduled for some pre-configured amount of time
        """
        _i.ProcessContext_yieldProcessor(self._c)
    
    def relationshipAvailable(self, relationship:str) -> bool:
        """
        Returns whether the processor has available capacity on an outbound connections

        #### Parameters
        * relationship (str): The relationship name

        #### Returns
        true if the relationship has available capacity, false otherwise
        """
        return _i.ProcessContext_relationshipAvailable(self._c, relationship)



class InputStream(RawIOBase):
    """
    The InputStream class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def readable(self) -> bool:
        """
        The InputStream supports reading
        """
        return True

    def read(self, size:int = -1) -> bytes:
        """
        Read and return bytes from the stream.
        If size is specified, at most size bytes will be read,
        otherwise, read and return the remaining bytes in the stream.

        #### Parameters
        * size (int): Maximum number of bytes to return

        #### Returns
        Bytes read from the stream
        """
        return super().read(size)

    def readall(self) -> bytes:
        """
        Read and return the remaining bytes from the stream.

        #### Returns
        Bytes read from the stream
        """
        return super().readall()
     
    def readinto(self, bytes):
        """
        Read bytes into a pre-allocated, writable bytes-like object

        #### Parameters
        * bytes (bytes): Pre-allocated bytes-like object

        #### Returns
        The number of bytes read
        """
        return _i.InputStream_readinto(self._c, bytes)

    def readline(self, size=-1):
        """
        Read bytes from the stream until a newline or EOF
        If size is specified, at most size bytes will be read.

        #### Parameters
        * size (int): Maximum number of bytes to return

        #### Returns
        Bytes read from the stream
        """
        return super().readline(size)

    def readlines(self, hint=-1):
        return super().readlines(hint)



class TextInputStream(TextIOBase):
    """
    The TextInputStream class
    """
    __slots__ = '_tw'
    def __init__(self, inputstream:InputStream):
        self._tw = TextIOWrapper(inputstream)

    def readable(self) -> bool:
        """
        The TextInputStream supports reading
        """
        return self._tw.readable()

    def read(self, size:int = -1) -> str:
        """
        Read and return characters from the stream as a string.
        If size is specified, at most size characters will be read,
        otherwise, read and return the remaining characters in the stream.

        #### Parameters
        * size (int): Maximum number of characters to return

        #### Returns
        Characters read from the stream as a string
        """
        return self._tw.read(size)

    def readall(self) -> str:
        """
        Read and return the remaining characters from the stream as a string.

        #### Returns
        Characters read from the stream as a string
        """
        return self.read()

    def readline(self, size:int = -1) -> str:
        """
        Read characters from the stream until a newline or EOF and return as a string.
        If size is specified, at most size characters will be read.

        #### Parameters
        * size (int): Maximum number of characters to return

        #### Returns
        Characters read from the stream as a string
        """
        return self._tw.readline(size)

    def readlines(self, hint=-1):
        return self._tw.readlines(hint)

    @property
    def encoding(self):
        """@private"""
        return self._tw.encoding

    @property
    def newlines(self):
        """@private"""
        return self._tw.newlines

    @property
    def errors(self):
        """@private"""
        return self._tw.errors



class OutputStream(RawIOBase):
    """
    The OutputStream class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
        
    def writable(self) -> bool:
        """
        The OutputStream supports writing
        """
        return True
    
    def write(self, bytesOrStr:bytes|str, *, encoding:str = None):
        """
        Write bytes or string to an OutputStream

        #### Parameters
        * bytesOrStr: bytes or string data
        * encoding (str): encoding to use for string inputs (default utf-8)

        #### Returns
        The number of bytes written
        """
        return _i.OutputStream_write(self._c, bytesOrStr.encode(encoding=text_encoding(encoding)) if isinstance(bytesOrStr, str) else bytesOrStr)

    def writeFromReadable(self, readable:IOBase):
        """
        Transfer from a readable text or binary IOBase to an OutputStream

        #### Parameters
        * readable (`IOBase`): A readable stream
        """
        istext = isinstance(readable,TextIOBase)
        while True:
            line = readable.readline(4096)
            if not line:
                break
            self.write(line, encoding=readable.encoding if istext else None)

    def writelines(self, lines):
        for line in lines:
            self.write(line)



class TextOutputStream(TextIOBase):
    """
    The TextOutputStream class
    """
    __slots__ = '_tw'
    def __init__(self, outputstream:OutputStream):
        self._tw = TextIOWrapper(outputstream, write_through=True)

    def writable(self) -> bool:
        """
        The TextOutputStream supports writing
        """
        return self._tw.writable()
    
    def write(self, bytesOrStr, *, encoding:str = None):
        """
        Write bytes or string to a TextOutputStream

        #### Parameters
        * bytesOrStr: bytes or string data
        * encoding (str): encoding to use for bytes inputs (default utf-8)

        #### Returns
        The number of bytes written
        """
        return self._tw.write(bytesOrStr if isinstance(bytesOrStr, str) else bytesOrStr.decode(encoding=text_encoding(encoding)) )

    def writeFromReadable(self, readable:IOBase, *, encoding:str = None):
        """
        Transfer from a readable text or binary IOBase to a TextOutputStream

        #### Parameters
        * readable (`IOBase`): A readable stream
        * encoding (str): encoding to use for bytes inputs (default utf-8)
        """
        istext = isinstance(readable,TextIOBase)
        while True:
            line = readable.readline(4096)
            if not line:
                break
            self.write(line, encoding=None if istext else encoding)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    @property
    def encoding(self):
        """@private"""
        return self._tw.encoding

    @property
    def newlines(self):
        """@private"""
        return self._tw.newlines

    @property
    def errors(self):
        """@private"""
        return self._tw.errors



class FlowFile:
    """
    The FlowFile class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    
    def getUuid(self) -> str:
        """
        #### Returns
        The unique identifier for this FlowFile
        """
        return _i.FlowFile_getUuid(self._c)
        
    def getAttribute(self, name:str) -> str:
        """
        Obtains the attribute value for the given key

        #### Parameters
        * name (str): Attribute name

        #### Returns
        The attribute value
        """
        return _i.FlowFile_getAttribute(self._c, name)
        
    def getAttributes(self) -> dict[str,str]:
        """
        #### Returns
        A dictionary all of the FlowFile attributes
        """
        return _i.FlowFile_getAttributes(self._c)
        
    def getSize(self) -> int:
        """
        #### Returns
        The size of the FlowFile contents in bytes
        """
        return _i.FlowFile_getSize(self._c)



_tp_lock = Lock()
_tp_threads = []

class _tp_thread(Thread):
    __slots__ = (
        'cond','stop','target','args')
    def __init__(self):
        super().__init__(daemon=True)
        self.cond = Condition()
        self.stop = False
        self.target = None
        self.args = ()
    def run(self):
        with self.cond:
            self.cond.notify()
            while not self.stop:
                self.stop = not self.cond.wait(timeout=20) or self.stop
                if self.target is not None:
                    try:
                        self.target(*self.args)
                    except:
                        pass #self.target should handle exceptions
                    self.target = None
                    self.args = ()
            self.cond.notify()

def _tp_exec(target, args=()):
    with _tp_lock:
        toRemove = []
        for t in _tp_threads:
            if t.cond.acquire(blocking=False):
                try:
                    if t.stop:
                        toRemove.append(t)
                    elif t.target is None:
                        t.args = args
                        t.target = target
                        t.cond.notify()
                        return
                finally:
                    t.cond.release()
        t = _tp_thread()
        _tp_threads.append(t)
        with t.cond:
            t.args = args
            t.target = target
            t.start()
            t.cond.wait()
            t.cond.notify()
        if toRemove:
            for t in toRemove:
                t.join()
                _tp_threads.remove(t)

def _tp_stop():
    with _tp_lock:
        threads = list(_tp_threads)
        for t in threads:
            with t.cond:
                t.stop = True
                t.cond.notify()
        for t in threads:
            t.join()
        _tp_threads.clear()



ArgT = TypeVar('ArgT')
class WithCallable(Generic[ArgT]):
    """
    'With' statement context manager returned by various functions that optionally accept a Callable argument

    For those function that support the WithCallable return type, if no Callable is provided in the
    argument list in a call to the function, the function will instead return an instance of WithCallable
    that should be used in a 'with' statement.

    #### Usage
    Read and write the entire `FlowFile` content via `ProcessSession.readWrite`
    ````
    with session.readWrite(flowfile) as (inputstream,outputstream):
        # Read from the inputstream and write to the outputstream to transform the flowfile content
        ...
    ````
    """
    __slots__ = (
        '_h','_c','_a','_e')
    def __init__(self, handler):
        self._h = handler
        self._c = Condition()
        self._a = None
        self._e = None

    def __enter__(self) -> ArgT:
        def callableThreadFn():
            with self._c:
                def callableFn(*arg):
                    self._a = arg[0] if len(arg) == 1 else arg
                    self._c.notify()
                    self._c.wait()
                try:
                    self._h(callableFn)
                except Exception as e:
                    self._e = e
                finally:
                    self._a = None
                    self._c.notify()
        with self._c:
            _tp_exec(target=callableThreadFn)
            self._c.wait()
            if self._e is not None:
                raise self._e
            if self._a is not None:
                return self._a

    def __exit__(self, exc_type, exc_value, traceback):
        with self._c:
            self._c.notify()
            if self._a is not None:
                self._a = None
                self._c.wait()
        if exc_type is None and self._e is not None:
            raise self._e



class ProcessSession:
    """
    The ProcessSession class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule

    def putAttribute(self, flowfile:FlowFile, name:str, value:str) -> FlowFile:
        """
        Adds an attribute to the `FlowFile`

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * name (str): Attribute name
        * value (str): Attribute value

        #### Returns
        The updated `FlowFile`
        """
        return _i.ProcessSession_putAttribute(self._c, flowfile, name, value)

    def putAttributes(self, flowfile:FlowFile, attributes:dict[str,str]) -> FlowFile:
        """
        Adds attributes to the `FlowFile` from the given dictionary
        
        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * attributes (dict): Dictionary of attributes

        #### Returns
        The updated `FlowFile`
        """
        return _i.ProcessSession_putAttributes(self._c, flowfile, attributes)
        
    def removeAttribute(self, flowfile:FlowFile, name:str) -> FlowFile:
        """
        Remove an attribute from a `FlowFile`

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * name (str): Attribute name

        #### Returns
        The updated `FlowFile`
        """
        return _i.ProcessSession_removeAttribute(self._c, flowfile, name)
        
    def removeAttributes(self, flowfile:FlowFile, names:list[str] = [], *, pattern:str = None) -> FlowFile:
        """
        Remove attributes from a `FlowFile` by names or by matching a pattern

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * names (list): List of attribute names
        * pattern (str): Pattern string to match multiple attribute names

        #### Returns
        The updated `FlowFile`
        """
        return _i.ProcessSession_removeAttributes(self._c, flowfile, names, '' if pattern is None else pattern)

    def read(self, flowfile:FlowFile, reader:Callable[[InputStream],None] = None) -> WithCallable[InputStream]|None:
        """
        Executes the given callable against the contents corresponding to the given `FlowFile`

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>
        
        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * reader (Callable): Callable accepting an `InputStream`
        """
        if reader is not None:
            _i.ProcessSession_read(self._c, flowfile, reader)
        else:
            return WithCallable[InputStream](lambda c: _i.ProcessSession_read(self._c, flowfile, c))

    def remove(self, flowfile:FlowFile):
        """
        Remove the `FlowFile` from the session
        
        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        """
        _i.ProcessSession_remove(self._c, flowfile)

    def transfer(self, flowfile:FlowFile, relationship:str = None):
        """
        Transfer the `FlowFile` to the named output relationship or back to the input queue

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * relationship (str): The output relationship name
        """
        _i.ProcessSession_transfer(self._c, flowfile, '' if relationship is None else relationship)

    def write(self, flowfile:FlowFile, writer:Callable[[OutputStream],None] = None) -> WithCallable[OutputStream]|None:
        """
        Executes the given callable against the content corresponding to the given `FlowFile`

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * writer (Callable): Callable accepting an `OutputStream`
        """
        if writer is not None:
            _i.ProcessSession_write(self._c, flowfile, writer)
        else:
            return WithCallable[OutputStream](lambda c: _i.ProcessSession_write(self._c, flowfile, c))

    def readWrite(self, flowfile:FlowFile, readerWriter:Callable[[InputStream,OutputStream],None] = None) -> WithCallable[tuple[InputStream,OutputStream]]|None:
        """
        Executes the given callable against the content corresponding to the given `FlowFile`

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>
        
        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`
        * readerWriter (Callable): Callable accepting an `InputStream` and an `OutputStream`
        """
        if readerWriter is not None:
            _i.ProcessSession_readWrite(self._c, flowfile, readerWriter)
        else:
            return WithCallable[tuple[InputStream,OutputStream]](lambda c: _i.ProcessSession_readWrite(self._c, flowfile, c))

    def penalize(self, flowfile:FlowFile) -> FlowFile:
        """
        Penalize the `FlowFile` for the penalty duration

        #### Parameters
        * flowfile (`FlowFile`): The `FlowFile`

        #### Returns
        The penalized `FlowFile`
        """
        return _i.ProcessSession_penalize(self._c, flowfile)
        
    def get(self, *, maxResults:int = None) -> FlowFile|list[FlowFile]:
        """
        Returns one `FlowFile` or a list of up to maxResults FlowFiles from the input queue

        #### Parameters
        * maxResults (int): If specified, the maximum number of FlowFiles to return as a list

        #### Returns
        One `FlowFile`, a list of FlowFiles, or None
        """
        return _i.ProcessSession_get(self._c, -1 if maxResults is None else maxResults)
        
    def getQueueSize(self) -> int:
        """
        #### Returns
        The number of FlowFiles in the input queue
        """
        return _i.ProcessSession_getQueueSize(self._c)

    def commit(self):
        """
        Commits the current session ensuring all operations against FlowFiles within this session are atomically persisted
        """
        _i.ProcessSession_commit(self._c)

    def rollback(self):
        """
        Reverts any changes made during this session
        """
        _i.ProcessSession_rollback(self._c)
        
    def create(self, parent:FlowFile = None) -> FlowFile:
        """
        Creates a new `FlowFile`, optionally with parent linkage

        #### Parameters
        * parent (`FlowFile`): Optional parent `FlowFile`

        #### Returns
        The created `FlowFile`
        """
        return _i.ProcessSession_create(self._c, parent)
        
    def asFlowFileDocument(self, flowfile:FlowFile) -> 'FlowFileDocument':
        """
        Get a `FlowFileDocument` representation of the `FlowFile` for reading and writing IDOL document format

        #### Parameters
        *flowfile (`FlowFile`): The source `FlowFile`

        #### Returns
        The `FlowFileDocument` for the `FlowFile`
        """
        return _i.ProcessSession_asFlowFileDocument(self._c, flowfile)



PageSeparator:str = '\x0C'
"""
Page separator character ('\\x0C') used in document content text

Can be used by `DocumentAction.addContent` or content operations on `ContentAction`
"""

class ReadMode(Enum):
    """
    Enumeration for the FlowFile document update operation when reading a part
    """
    READ = 0
    """
    Read the part only

    For a modifying document action, a separate write or delete operation will be required
    """
    READ_AND_KEEP = 1
    """
    Read the part and keep it unchanged in the document
    """



class XmlElement:
    """
    The XmlElement class representing an element of the document XML metadata
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
    def __getitem__(self, name:str) -> 'XmlElement|str':
        """@public
        Get or add a child element with the given name
        (or attribute when the name starts with '@')
        """
        if name.startswith('@'):
            return self.getAttribute(name[1:])
        else:
            return self.getOrAddChild(name)

    def __setitem__(self, name:str, value:str):
        """@public
        Set the value of a child element with the given name
        (or attribute when the name starts with '@')
        """
        if name.startswith('@'):
            self.setAttribute(name[1:], value)
        else:
            if isinstance(value, XmlElement):
                elmt = self.getOrAddChild(name)
                for attr in elmt.getAttributes():
                    self.removeAttribute(attr)
                for child in elmt.getChildren():
                    child.remove()
                elmt.setValue(value.getValue())
                for attr, attrvalue in value.getAttributes().items():
                    elmt.setAttribute(attr, attrvalue)
                elmt.appendChildren(value)
            else:
                self.getOrAddChild(name).setValue(value)

    def __delitem__(self, name:str):
        """@public
        Delete all child elements with the given name
        (or attribute when the name starts with '@')
        """
        if name.startswith('@'):
            self.removeAttribute(name[1:])
        else:
            for child in filter(lambda c: c.getName() == name, self.getChildren()):
                child.remove()

    def __iter__(self) -> Iterator['XmlElement']:
        """@public
        Iterator for the child elements
        """
        return iter(self.getChildren())

    def isNativeXml(self) -> bool:
        """
        #### Returns
        True if using a native XML implementation, False if using a Java XML implementation
        """
        return _i.XmlElement_isNativeXml(self._c)

    def getName(self) -> str:
        """
        #### Returns
        The name of the element
        """
        return _i.XmlElement_getName(self._c)

    def getValue(self) -> str:
        """
        #### Returns
        The value of the element
        """
        return _i.XmlElement_getValue(self._c)

    def setValue(self, value:str):
        """
        Set the value of the element

        #### Parameters
        * value (str): The value to assign to the element
        """
        _i.XmlElement_setValue(self._c, value)

    def getElementsByXPath(self, xpath:str) -> list['XmlElement']:
        """
        Relative to the current element, get the elements that match the given XPath

        #### Parameters
        * xpath (str): The XPath query string

        #### Returns
        The list of elements matching the XPath
        """
        return _i.XmlElement_getElementsByXPath(self._c, xpath)

    def getValuesByXPath(self, xpath:str) -> list[str]:
        """
        Relative to the current element, get the values of elements or attributes that match the given XPath

        #### Parameters
        * xpath (str): The XPath query string

        #### Returns
        The list of values for elements or attributes matching the XPath
        """
        return _i.XmlElement_getValuesByXPath(self._c, xpath)

    def hasAttribute(self, name:str) -> bool:
        """
        Test if the element has the named attribute

        #### Parameters
        * name (str): The attribute name

        #### Returns
        True if the element has the named attribute, False otherwise
        """
        return _i.XmlElement_hasAttribute(self._c, name)

    def getAttribute(self, name:str, defValue:str = None) -> str:
        """
        Get the named attribute value from the element or return a default value

        #### Parameters
        * name (str): The attribute name
        * defValue (str): Default value to return if the attribute does not exist

        #### Returns
        The attribute value or the default value or None
        """
        return _i.XmlElement_getAttribute(self._c, name, defValue)

    def setAttribute(self, name:str, value:str):
        """
        Set an attribute on the element

        #### Parameters
        * name (str): The attribute name
        * value (str): The attribute value
        """
        _i.XmlElement_setAttribute(self._c, name, value)

    def removeAttribute(self, name:str):
        """
        Remove the named attribute from the element

        #### Parameters
        * name (str): The attribute name
        """
        _i.XmlElement_removeAttribute(self._c, name)

    def getAttributes(self) -> dict[str,str]:
        """
        #### Returns
        A dictionary of all the attributes on the element
        """
        return _i.XmlElement_getAttributes(self._c)

    def getChildren(self) -> list['XmlElement']:
        """
        #### Returns
        A list of all the child elements of the element
        """
        return _i.XmlElement_getChildren(self._c)

    def addChild(self, name:str) -> 'XmlElement':
        """
        Add a child element with the given name

        #### Parameters
        * name (str): The name of the element to create

        #### Returns
        The new element
        """
        return _i.XmlElement_addChild(self._c, name)

    def getOrAddChild(self, name:str) -> 'XmlElement':
        """
        Get the first child element with the given name, or create one if it does not already exist

        #### Parameters
        * name (str): The name of the element to get or create

        #### Returns
        The existing or new element
        """
        return _i.XmlElement_getOrAddChild(self._c, name)

    def getFirstChild(self, name:str) -> 'XmlElement|None':
        """
        Get the first child element with the given name

        #### Parameters
        * name (str): The name of the element

        #### Returns
        The existing element or None
        """
        return _i.XmlElement_getFirstChild(self._c, name)

    def appendChild(self, element:'XmlElement') -> 'XmlElement':
        """
        Append an `XmlElement` to this element

        #### Parameters
        * element (`XmlElement`): The element to append

        #### Returns
        The appended element
        """
        return _i.XmlElement_appendChild(self._c, element)

    def appendChildren(self, parentElement:'XmlElement'):
        """
        Append the children of an `XmlElement` to this element

        #### Parameters
        * parentElement (`XmlElement`): The element whose children will be appended to this element
        """
        _i.XmlElement_appendChildren(self._c, parentElement)

    def replaceWith(self, newElement:'XmlElement'):
        """
        Replace this element with the provided element, invalidating this element

        #### Parameters
        * newElement (`XmlElement`): The element that will replace this element
        """
        _i.XmlElement_replaceWith(self._c, newElement)

    def replaceWith(self, xmlString:str):
        """
        Replace this element with the provided XML string, invalidating this element

        #### Parameters
        * xmlString (str): The XML string that will replace this element
        """
        _i.XmlElement_replaceWith(self._c, xmlString)

    def remove(self):
        """
        Remove this element from the XML
        """
        _i.XmlElement_remove(self._c)

    def toString(self) -> str:
        """
        #### Returns
        The string representation of this element 
        """
        return _i.XmlElement_toString(self._c)

    def __str__(self) -> str:
        return _i.XmlElement_toString(self._c)

class DocumentAction:
    """
    The DocumentAction class
    """
    __slots__ = '_c'
    def __init__(self, capsule):
        """@private"""
        self._c = capsule

    def isContentPart(self) -> bool:
        """
        #### Returns
        True when this supports operations on a content text part via `ContentAction`
        """
        return isinstance(self, ContentAction)

    def isFilePart(self) -> bool:
        """
        #### Returns
        True when this supports operations on any file part via `FileAction`
        """
        return isinstance(self, FileAction)

    def isEmbeddedFilePart(self) -> bool:
        """
        #### Returns
        True when this supports operations on an embedded file part via `ContentFileAction`
        """
        return isinstance(self, ContentFileAction)

    def isFilenamePart(self) -> bool:
        """
        #### Returns
        True when this supports operations on a filename part via `ContentFilenameAction`
        """
        return isinstance(self, ContentFilenameAction)

    def isExternalFilePart(self) -> bool:
        """
        #### Returns
        True when this supports operations on an external file part via `ExternalFileAction`
        """
        return isinstance(self, ExternalFileAction)

    def getAttributes(self) -> dict[str,str]:
        """
        Get a dictionary of all FlowFile attributes

        <div class="tip" markdown="1">Part attributes are excluded, they should be accessed through part operations</div>

        #### Returns
        A dictionary of all FlowFile attributes
        """
        return _i.DocumentAction_getAttributes(self._c)
    getFlowFileAttributes = getAttributes
    """@private"""

    def getAttribute(self, name:str, defValue:str = None) -> str:
        """
        Get a FlowFile attribute by name

        <div class="tip" markdown="1">Part attributes are excluded, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        * defValue (str): Default value

        #### Returns
        The attribute value or the provided default if the attribute does not exist
        """
        return _i.DocumentAction_getAttribute(self._c, name, defValue)
    getFlowFileAttribute = getAttribute
    """@private"""

    def setAttribute(self, name:str, value:str) -> 'DocumentAction':
        """
        Set a FlowFile attribute

        <div class="tip" markdown="1">Part attributes are ignored, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        * value (str): Attribute value
        """
        return _i.DocumentAction_setAttribute(self._c, name, value)
    setFlowFileAttribute = setAttribute
    """@private"""

    def removeAttribute(self, name:str) -> 'DocumentAction':
        """
        Remove a FlowFile attribute

        <div class="tip" markdown="1">Part attributes are ignored, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        """
        return _i.DocumentAction_removeAttribute(self._c, name)
    removeFlowFileAttribute = removeAttribute
    """@private"""

    def getXmlMetadata(self, native:bool = True) -> XmlElement:
        """
        Get the XML metadata for the document

        The native parameter can usually be ignored, and may only be beneficial for optimization

        #### Parameters
        * native (bool): True to use native implementation, False for Java implementation

        #### Returns
        The XML metadata root `XmlElement`
        """
        return _i.DocumentAction_getXmlMetadata(self._c, native)

    def getXmlMetadataString(self) -> str:
        """
        #### Returns
        The XML metadata for the document as a plain XML string
        """
        return _i.DocumentAction_getXmlMetadataString(self._c)

    def setXmlMetadataString(self, xmlMetadata:str):
        """
        Replace the document XML metadata with the plain XML string provided

        <div class="tip" markdown="1">The XML metadata can be updated via the XmlElement returned by `DocumentAction.getXmlMetadata`</div>

        #### Parameters
        * xmlMetadata (str): The new XML metadata string
        """
        _i.DocumentAction_setXmlMetadataString(self._c, xmlMetadata)

    def clearXmlMetadata(self):
        """
        Clear all elements from the XML metadata
        """
        _i.DocumentAction_clearXmlMetadata(self._c)

    def addFilename(self, filename:str, ownFile:bool, mimeType:str = None, *, displayName:str = None) -> 'FilePartAction':
        """
        Add a document part referencing a file on the filesystem

        #### Parameters
        * filename (str): The path and filename of an accessible file on the filesystem
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        * mimeType (str): The mime-type of the file
        * displayName (str): The display filename, used where a readable filename is useful

        #### Returns
        The `FilePartAction` for the newly created part providing access to the part attributes and metadata
        """
        return _i.DocumentAction_addFilename(self._c, filename, ownFile, displayName, mimeType)

    def addExternalFile(self, locator:'ExternalFileLocator', ownFile:bool, mimeType:str = None, *, displayName:str = None) -> 'FilePartAction':
        """
        Add a document part referencing a file stored externally

        #### Parameters
        * locator (`ExternalFileLocator`): The locator object specifying how to access the external file
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        * mimeType (str): The mime-type of the file
        * displayName (str): The display filename, used where a readable filename is useful

        #### Returns
        The `FilePartAction` for the newly created part providing access to the part attributes and metadata
        """
        return _i.DocumentAction_addExternalFile(self._c, locator, ownFile, displayName, mimeType)

    def addFile(self, fileStreamer:InputStream|IOBase|Callable[[OutputStream],None] = None, displayName:str = None, mimeType:str = None) -> WithCallable[OutputStream]|'FilePartAction':
        """
        Add a document part that embeds a file

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * fileStreamer (InputStream|IOBase|Callable): The input stream or stream writer
        * displayName (str): The display filename, used where a readable filename is useful
        * mimeType (str): The mime-type of the file

        #### Returns
        The `FilePartAction` for the newly created part providing access to the part attributes and metadata (unless using `WithCallable`)
        """
        if fileStreamer is not None:
            if not isinstance(fileStreamer, InputStream) and isinstance(fileStreamer, IOBase):
                return _i.DocumentAction_addFile(self._c, lambda o: o.writeFromReadable(fileStreamer), displayName, mimeType)
            else:
                return _i.DocumentAction_addFile(self._c, fileStreamer, displayName, mimeType)
        else:
            return WithCallable[OutputStream](lambda c: _i.DocumentAction_addFile(self._c, c, displayName, mimeType))

    def addContent(self, contentStreamer:list[str]|str|InputStream|IOBase|Callable[[TextOutputStream],None] = None) -> WithCallable[TextOutputStream]|'DocumentPartAction':
        """
        Add a content text part

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * contentStreamer (str|InputStream|IOBase|Callable): The content string, input stream or stream writer

        #### Returns
        The `DocumentPartAction` for the newly created part providing access to the part attributes and metadata (unless using `WithCallable`)
        """
        if contentStreamer is not None:
            if not isinstance(contentStreamer, InputStream) and isinstance(contentStreamer, IOBase):
                return _i.DocumentAction_addContent(self._c, lambda o: o.writeFromReadable(contentStreamer))
            else:
                return _i.DocumentAction_addContent(self._c, PageSeparator.join(contentStreamer) if isinstance(contentStreamer, list) else contentStreamer)
        else:
            return WithCallable[TextOutputStream](lambda c: _i.DocumentAction_addContent(self._c, c))

    def deleteFileOnCommit(self, filename):
        """
        Register a clean-up action to delete the specified file when the current session is committed

        #### Parameters
        * filename (str): The filename of an accessible file to delete on commit
        """
        _i.DocumentAction_deleteFileOnCommit(self._c, filename)

    def deleteFileOnRollback(self, filename:str):
        """
        Register a clean-up action to delete the specified file when the current session is rolled back

        #### Parameters
        * filename (str): The filename of an accessible file to delete on rollback
        """
        _i.DocumentAction_deleteFileOnRollback(self._c, filename)

class DocumentPartAction(DocumentAction):
    """
    The DocumentPartAction class
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)
        
    def getPartId(self) -> int:
        """
        #### Returns
        The document part ID
        """
        return _i.DocumentPartAction_getPartId(self._c)

    def getPartAttributes(self) -> dict[str,str]:
        """
        #### Returns
        A dictionary of part attributes for the current part
        """
        return _i.DocumentPartAction_getPartAttributes(self._c)

    def getPartAttribute(self, name:str, defValue:str = None) -> str:
        """
        Get a part attribute for the current part by name
        
        #### Parameters
        * name (str): Attribute name
        * defValue (str): Default value

        #### Returns
        The part attribute value or the provided default if the part attribute does not exist
        """
        return _i.DocumentPartAction_getPartAttribute(self._c, name, defValue)

    def setPartAttribute(self, name:str, value:str) -> 'DocumentPartAction':
        """
        Set a part attribute for the current part
        
        #### Parameters
        * name (str): Attribute name
        * value (str): Attribute value
        """
        return _i.DocumentPartAction_setPartAttribute(self._c, name, value)

    def removePartAttribute(self, name:str) -> 'DocumentPartAction':
        """
        Remove a part attribute for the current part
        
        #### Parameters
        * name (str): Attribute name
        """
        return _i.DocumentPartAction_removePartAttribute(self._c, name)

    def getPartXmlMetadata(self, native:bool = True):
        """
        Get the part XML metadata for the current part

        The native parameter can usually be ignored, and may only be beneficial for optimization

        #### Parameters
        * native (bool): True to use native implementation, False for Java implementation

        #### Returns
        The part XML metadata root `XmlElement` for the current part
        """
        return _i.DocumentPartAction_getPartXmlMetadata(self._c, native)

    def deletePart(self):
        """
        Delete the current part
        """
        _i.DocumentPartAction_deletePart(self._c)
    
class ContentAction(DocumentPartAction):
    """
    The ContentAction class (Actions for text content parts)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)

    def readContent(self, pageReader:Callable[[TextInputStream],None] = None, wholePartConsumer:bool = False, readMode:ReadMode = ReadMode.READ) -> WithCallable[TextInputStream]|None:
        """
        Read the pages of content text

        The pageReader is called for each page in the part, or once for the whole part if wholePartConsumer=True.

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable` (enforces wholePartConsumer=True)</div>

        <div class="tip" markdown="1">Use `ContentAction.getContent` to retrieve all pages as a list</div>

        #### Parameters
        * pageReader (Callable): Callable accepting a `TextInputStream`
        * wholePartConsumer (bool): True for pageReader to be called once for whole part, False for one call per page in part
        * readMode (`ReadMode`): `ReadMode.READ` or `ReadMode.READ_AND_KEEP`
        """
        if pageReader is not None:
            if wholePartConsumer is True or wholePartConsumer is False:
                _i.ContentAction_readContent(self._c, pageReader, wholePartConsumer, readMode.value)
            else: #For compatibility with readMode as second positional argument
                _i.ContentAction_readContent(self._c, pageReader, False, wholePartConsumer.value)
        else:
            return WithCallable[TextInputStream](lambda c: _i.ContentAction_readContent(self._c, c, True, readMode.value))

    def transformContent(self, pageReadWriter:Callable[[TextInputStream,TextOutputStream],None] = None, wholePartConsumer:bool = False) -> WithCallable[tuple[TextInputStream,TextOutputStream]]|None:
        """
        Transform the pages of content text

        The pageReadWriter is called for each page in the part, or once for the whole part if wholePartConsumer=True.

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable` (enforces wholePartConsumer=True)</div>

        <div class="tip" markdown="1">Use `ContentAction.getContent` and `ContentAction.setContent` to get and set all text content pages in this part</div>

        #### Parameters
        * pageReadWriter (Callable): Callable accepting a `TextInputStream` and a `TextOutputStream`
        * wholePartConsumer (bool): True for pageReadWriter to be called once for whole part, False for one call per page in part
        """
        if pageReadWriter is not None:
            _i.ContentAction_transformContent(self._c, pageReadWriter, wholePartConsumer)
        else:
            return WithCallable[tuple[TextInputStream,TextOutputStream]](lambda c: _i.ContentAction_transformContent(self._c, c, True))

    def writeContent(self, contentWriter:Callable[[TextOutputStream],None] = None) -> WithCallable[TextOutputStream]|None:
        """
        Write the content text

        The contentWriter is called once for the part.  Use `PageSeparator` to split the part into pages

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        <div class="tip" markdown="1">Use `ContentAction.setContent` to replace all text content in this part from a list or string</div>

        #### Parameters
        * contentWriter (Callable): Callable accepting a `TextOutputStream`
        """
        if contentWriter is not None:
            _i.ContentAction_writeContent(self._c, contentWriter)
        else:
            return WithCallable[TextOutputStream](lambda c: _i.ContentAction_writeContent(self._c, c))

    def getContent(self, readMode:ReadMode = ReadMode.READ) -> list[str]:
        """
        Get an array of strings containing the text content pages stored in this part

        #### Parameters
        * readMode (`ReadMode`): `ReadMode.READ` or `ReadMode.READ_AND_KEEP`

        #### Returns
        Array of text content page strings
        """
        contents = []
        def reader(inputstream):
            contents.append(inputstream.readall())
        self.readContent(reader, readMode)
        return contents
        
    def setContent(self, contents:list[str]|str):
        """
        Set the text content pages stored in this part

        #### Parameters
        * contents: List of strings or a single string
        """
        def writer(outputstream):
            outputstream.write(contents if isinstance(contents, str) else PageSeparator.join(contents))
        self.writeContent(writer)

class FilePartAction(DocumentPartAction):
    """
    The FilePartAction class (Base class for action on file parts for file related attribute updates)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)

    def setFileMimeType(self, mimeType:str) -> 'FilePartAction':
        """
        Set the mime-type attribute for the current file storage part

        #### Parameters
        * mimeType (str): The mime-type string
        """
        return _i.FileAction_setFileMimeType(self._c, mimeType)

    def setFileDisplayName(self, displayName:str) -> 'FilePartAction':
        """
        Set the display filename for the current file storage part, used where a readable filename is useful

        #### Parameters
        * displayName (str): The display filename
        """
        return _i.FileAction_setFileDisplayName(self._c, displayName)

class FileAction(FilePartAction):
    """
    The FileAction class (Base class for action on file parts with differing storage)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)
        
    def setTempDirectory(self, tempDirectory:str):
        """
        Set the temporary directory used by some file operations

        #### Parameters
        * tempDirectory (str): Temporary directory string
        """
        _i.FileAction_setTempDirectory(self._c, tempDirectory)

    def readAsFilename(self, handler:Callable[[str],None] = None, readMode:ReadMode = ReadMode.READ) -> WithCallable[str]|None:
        """
        Read the file storage via a filename passed to the provided callable

        For embedded or external file storage, the file will be written to a temporary file first

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * handler (Callable): Callable accepting a filename string
        * readMode (`ReadMode`): `ReadMode.READ` or `ReadMode.READ_AND_KEEP`
        """
        if handler is not None:
            _i.FileAction_readAsFilename(self._c, handler, readMode.value)
        else:
            return WithCallable[str](lambda c: _i.FileAction_readAsFilename(self._c, c, readMode.value))

    def transformAsFilename(self, transformer:Callable[[str],str], ownFile:bool):
        """
        Transform the file storage via a filename passed to the provided callable

        For embedded or external file storage, the file will be written to a temporary file first
        
        The value returned by the callable should be a filename containing the new file data that
        will replace the existing file storage

        #### Parameters
        * transformer (Callable): Callable accepting a filename string and returning a filename string
        * ownFile (bool): True if the resulting file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        """
        _i.FileAction_transformAsFilename(self._c, transformer, ownFile)

    def readFile(self, reader:Callable[[InputStream],None] = None, readMode:ReadMode = ReadMode.READ) -> WithCallable[InputStream]|None:
        """
        Read the file storage via a callable

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * reader (Callable): Callable accepting an `InputStream`
        * readMode (`ReadMode`): `ReadMode.READ` or `ReadMode.READ_AND_KEEP`
        """
        if reader is not None:
            _i.FileAction_readFile(self._c, reader, readMode.value)
        else:
            return WithCallable[InputStream](lambda c: _i.FileAction_readFile(self._c, c, readMode.value))

    def transformFile(self, readWriter:Callable[[InputStream,OutputStream],None] = None) -> WithCallable[tuple[InputStream,OutputStream]]|None:
        """
        Transform the file storage via a callable

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * handler (Callable): Callable accepting an `InputStream` and an `OutputStream`
        """
        if readWriter is not None:
            _i.FileAction_transformFile(self._c, readWriter)
        else:
            return WithCallable[tuple[InputStream,OutputStream]](lambda c: _i.FileAction_transformFile(self._c, c))

    def transferToFile(self, readWriter:Callable[[InputStream,OutputStream],None] = None):
        """
        Transfer the current file storage to embedded file storage, with optional transform

        #### Parameters
        * readWriter (Callable): Callable accepting an `InputStream` and an `OutputStream`
        """
        _i.FileAction_transferToFile(self._c, readWriter)

    def transferToFilename(self, filename:str, ownFile:bool, readWriter:Callable[[InputStream,OutputStream],None] = None):
        """
        Transfer the current file storage to a filename on the filesystem, with optional transform

        #### Parameters
        * filename (str): The path and filename of an accessible file on the filesystem
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        * readWriter (Callable): Callable accepting an `InputStream` and an `OutputStream`
        """
        _i.FileAction_transferToFilename(self._c, filename, ownFile, readWriter)

    def transferToExternalFile(self, locator:'ExternalFileLocator', ownFile:bool, readWriter:Callable[[InputStream,OutputStream],None] = None):
        """
        Transfer the current file storage to external file storage, with optional transform

        #### Parameters
        * locator (`ExternalFileLocator`): The locator object specifying how to access the external file
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        * readWriter (Callable): Callable accepting an `InputStream` and an `OutputStream`
        """
        _i.FileAction_transferToExternalFile(self._c, locator, ownFile, readWriter)

class ContentFileAction(FileAction):
    """
    The ContentFileAction class (Actions for embedded file parts)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)
        
    def writeFile(self, writer:Callable[[OutputStream],None] = None) -> WithCallable[OutputStream]|None:
        """
        Write the binary content of the embedded file part

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * writer (Callable): Callable accepting an `OutputStream` 
        """
        if writer is not None:
            _i.ContentFileAction_writeFile(self._c, writer)
        else:
            return WithCallable[OutputStream](lambda c: _i.ContentFileAction_writeFile(self._c, c))

class ContentFilenameAction(FileAction):
    """
    The ContentFilenameAction class (Actions for filename parts referencing files on the filesystem)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)
        
    def hasOwnership(self) -> bool:
        """
        #### Returns
        True if the current part has ownership of the file on the filesystem, False otherwise
        """
        return _i.ContentFilenameAction_hasOwnership(self._c)

    def disownFile(self):
        """
        Disown the file if the current part has ownership of the file on the filesystem
        """
        _i.ContentFilenameAction_disownFile(self._c)

    def exists(self) -> bool:
        """
        #### Returns
        True if the current part references a file on the filesystem that exists, False otherwise
        """
        return _i.ContentFilenameAction_exists(self._c)

    def getFilename(self) -> str:
        """
        #### Returns
        The path and filename of the file on the filesystem referenced by the current part
        """
        return _i.ContentFilenameAction_getFilename(self._c)

    def replaceFilename(self, filename:str, ownFile:bool):
        """
        Replace the filename for this part to point at a different file on the filesystem

        #### Parameters
        * filename (str): The path and filename of an accessible file on the filesystem
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        """
        _i.ContentFilenameAction_replaceFilename(self._c, filename, ownFile)

    def readFile(self, reader:Callable[[InputStream],None] = None, readMode:ReadMode = ReadMode.READ) -> WithCallable[InputStream]|None:
        """
        Read the file referenced by the current part

        <div class="tip" markdown="1">Supports 'with' statement via `WithCallable`</div>

        #### Parameters
        * reader (Callable): Callable accepting an `InputStream`
        * readMode (`ReadMode`): `ReadMode.READ` or `ReadMode.READ_AND_KEEP`
        """
        if reader is not None:
            _i.ContentFilenameAction_readFile(self._c, reader, readMode.value)
        else:
            return WithCallable[InputStream](lambda c: _i.ContentFilenameAction_readFile(self._c, c, readMode.value))

class ExternalFileLocator:
    """
    The ExternalFileLocator class

    The class is constructed from two arguments, the first is a string which may be one of

    * 'JavaClassName',
    * '#ServiceKey' or
    * 'JavaClassName#ServiceKey'

    and a dictionary of location properties

    The JavaClassName if specified, is the full name of the Java class that provides access to the external file storage

    The ServiceKey if specified, should be the value of the Service Key property configured for an IdolFlowFileService,
    this service can be used to configure various cloud storage for use as external storage
    """
    __slots__ = (
        '_javaClassNameAndServiceKey',
        '_javaClassName',
        '_serviceKey',
        '_locationProperties')
    def __init__(self, javaClassNameAndServiceKey, locationProperties = {}):
        self._javaClassNameAndServiceKey = javaClassNameAndServiceKey
        s = javaClassNameAndServiceKey.split('#', 1)
        self._javaClassName = s[0]
        self._serviceKey = s[1] if len(s) > 1 else ''
        self._locationProperties = locationProperties
    
    def getClassNameAndServiceKey(self) -> str:
        """
        Returns
        The class name and service key string
        """
        return self._javaClassNameAndServiceKey

    def getClassName(self) -> str:
        """
        Returns
        The class name string
        """
        return self._javaClassName

    def getServiceKey(self) -> str:
        """
        Returns
        The service key string
        """
        return self._serviceKey

    def getLocationProperties(self) -> dict[str,str]:
        """
        Returns
        The dictionary of location properties
        """
        return self._locationProperties

class ExternalFileAction(FileAction):
    """
    The ExternalFileAction class (Actions for external file parts referencing files in external storage)
    """
    __slots__ = ()
    def __init__(self, capsule):
        """@private"""
        super().__init__(capsule)
        
    def hasOwnership(self) -> bool:
        """
        #### Returns
        True if the current part has ownership of the external file, False otherwise
        """
        return _i.ExternalFileAction_hasOwnership(self._c)

    def disownFile(self):
        """
        Disown the file if the current part has ownership of the external file
        """
        _i.ExternalFileAction_disownFile(self._c)

    def exists(self) -> bool:
        """
        #### Returns
        True if the current part references an external file that exists, False otherwise
        """
        return _i.ExternalFileAction_exists(self._c)

    def getLocator(self) -> ExternalFileLocator:
        """
        #### Returns
        The `ExternalFileLocator` for the current part
        """
        return _i.ExternalFileAction_getLocator(self._c)

    def replaceLocator(self, locator:ExternalFileLocator, ownFile:bool):
        """
        Replace the locator for this part to point at a different external file

        #### Parameters
        * locator (`ExternalFileLocator`): The new locator object specifying how to access the external file
        * ownFile (bool): True if the file should be owned by the document; unless disowned later, the file will be deleted when no longer used by the document
        """
        _i.ExternalFileAction_replaceLocator(self._c, locator, ownFile)

    def getDownloadUrl(self) -> str|None:
        """
        Get a download URL for the external file referenced by the current part
        
        This may be a signed time-limited URL

        If a download URL is not supported by the external storage, None is returned

        #### Returns
        The download URL for the external file, or None if not supported
        """
        return _i.ExternalFileAction_getDownloadUrl(self._c);



class DocMod(dict):
    """
    The DocMod class - an alternative to using `DocumentModifier` with methods
    in `FlowFileDocument` by defining the implementation in a derived class.

    ### Example
    All the action methods below may optionally be specified.
    Additional state may be stored as attributes in the base dictionary.

    ````
    class MyDocMod(DocMod):
        
        def preAction(self, action: DocumentAction):
            self.mystate = "something"
        
        #def onContent(self, action: ContentAction): ...
        #def defaultFileAction(self, action: FileAction): ...
        #def onContentFile(self, action: ContentFileAction): ...
        #def onContentFilename(self, action: ContentFilenameAction): ...
        #def onExternalFile(self, action: ExternalFileAction): ...
        
        def postAction(self, action: DocumentAction):
            # Do something maybe using self.mystate or self.handlerstate
            ...
    ````

    #### Usage
    ````
    doc.modify(MyDocMod({"handlerstate": "something"}))
    ````
    """
    __getattr__ = dict.get
    """@public"""
    __setattr__ = dict.__setitem__
    """@public"""
    __delattr__ = dict.__delitem__
    """@public"""
    def __bool__(self): return True
    preAction = None
    onContent = None
    defaultFileAction = None
    onContentFile = None
    onContentFilename = None
    onExternalFile = None
    postAction = None

class DocumentModifier:
    """
    The DocumentModifier class

    This class provides access through a set of callables to the parts and metadata
    of a FlowFileDocument.

    #### Usage
    Using callables
    ````
    def myOnContentFilenameFunction(action: ContentFilenameAction):
        # Do something with the filename part
        ...

    document.modify(DocumentModifier()
        .onContentFilename(myOnContentFilenameFunction))
    ````
    
    Using a class (see `DocMod`)
    ````
    class MyDocMod(DocMod):

        def __init__(self):
            #Initialization
            ...

        def onContentFilename(self, action: ContentFilenameAction):
            # Do something with the filename part
            ...

    document.modify(MyDocMod())
    ````
    """
    __slots__ = (
        '_preAction',
        '_onContent',
        '_onContentFile',
        '_onContentFilename',
        '_onExternalFile',
        '_postAction')
    def __init__(self, docMod : DocMod | None = None):
        for slot in self.__slots__:
            setattr(self, slot, None)
        if docMod is not None:
            if docMod.preAction is not None:
                self.preAction(docMod.preAction)
            if docMod.onContent is not None:
                self.onContent(docMod.onContent)
            if docMod.defaultFileAction is not None:
                self.defaultFileAction(docMod.defaultFileAction)
            if docMod.onContentFile is not None:
                self.onContentFile(docMod.onContentFile)
            if docMod.onContentFilename is not None:
                self.onContentFilename(docMod.onContentFilename)
            if docMod.onExternalFile is not None:
                self.onExternalFile(docMod.onExternalFile)
            if docMod.postAction is not None:
                self.postAction(docMod.postAction)
    
    def preAction(self, fn: Callable[[DocumentAction], None]) -> Self:
        self._preAction = fn
        return self
    def onContent(self, fn: Callable[[ContentAction], None]) -> Self:
        self._onContent = fn
        return self
    def defaultFileAction(self, fn: Callable[[FileAction], None]) -> Self:
        for slot in ['_onContentFile', '_onContentFilename', '_onExternalFile']:
            if getattr(self, slot) is None:
                setattr(self, slot, fn)
        return self
    def onContentFile(self, fn: Callable[[ContentFileAction], None]) -> Self:
        self._onContentFile = fn
        return self
    def onContentFilename(self, fn: Callable[[ContentFilenameAction], None]) -> Self:
        self._onContentFilename = fn
        return self
    def onExternalFile(self, fn: Callable[[ExternalFileAction], None]) -> Self:
        self._onExternalFile = fn
        return self
    def postAction(self, fn: Callable[[DocumentAction], None]) -> Self:
        self._postAction = fn
        return self



class WithPartsDocumentAction(DocumentAction):
    """
    The WithPartsDocumentAction is the target type of the 'With' statement context
    manager `WithDocumentAction` with support for all `DocumentAction` operations,
    plus access to document parts via the `WithPartsDocumentAction.parts` generator
    """
    __slots__ = (
        '_wda')
    def __init__(self, wda, action):
        super().__init__(action._c)
        self._wda = wda

    def restart(self, wda:'WithDocumentAction'):
        """
        Explicitly restart operations on the `FlowFileDocument`,
        specifying the access required by passing a constructed `WithDocumentAction`

        Any previous operations performed will have been fully applied to the `FlowFile`

        #### Parameters
        * wda (WithDocumentAction): `WithDocumentAction` returned by, for example `FlowFileDocument.modifying`

        #### Usage
        ````
        with doc.reading() as action:
            # Perform reading operations
            action.restart(doc.modifying())
            # Perform modifying operations
        ````
        """
        self._wda.__exit__(None, None, None)
        self._wda._ffdoc = wda._ffdoc
        self._wda._mod = wda._mod
        self._c = self._wda.__enter__()._c

    def parts(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A generator for `DocumentPartAction` instances for accessing document context text and file parts

        #### Usage
        ````
        with doc.modifying() as action:
            for part in action.parts():
                if part.isContentPart():
                    # Perform actions for any content text part
                # elif part.isXXX():
        ````
        """
        return self._wda._ffdoc._parts(self._wda)

class WithDocumentAction:
    """
    The WithDocumentAction class can be used to begin operating on a `FlowFileDocument`
    and is used to manage access to the underlying FlowFile content stream.

    This can be used as a simpler alternative to the `DocMod` and `DocumentModifier` classes
    by reducing the need for Callable or class implementations that those classes require

    Many functions on `FlowFileDocument` can implicitly use WithDocumentAction and allowing
    direct and repeated calls from the processor handler function

    This 'with' statement context manager can be created via these methods on `FlowFileDocument`:
        
    * `FlowFileDocument.reading`
    * `FlowFileDocument.updatingAttributes`
    * `FlowFileDocument.appending`
    * `FlowFileDocument.modifying`
    * `FlowFileDocument.overwriting`

    The target type of the 'with' statement is `WithPartsDocumentAction`, providing access to
    the parts via `WithPartsDocumentAction.parts` and to all operations on `DocumentAction`

    #### Usage
    ````
    with doc.modifying() as action:
        # Operate using the provided `WithPartsDocumentAction` that extends `DocumentAction`
        # Access the content text and file parts using `WithPartsDocumentAction.parts`
        ...
    ````
    """
    __slots__ = (
        '_ffdoc','_mod')
    def __init__(self, ffdoc, modifierMethod):
        self._ffdoc = ffdoc
        self._mod = modifierMethod

    def __enter__(self) -> WithPartsDocumentAction:
        if self._ffdoc._w is not None or self._ffdoc._p is True:
            raise RuntimeError('FlowFileDocument operations already in progress')
        self._ffdoc._i = True
        i = iter(self._ffdoc._parts(self))
        self._ffdoc._w = WithPartsDocumentAction(self, next(i))
        self._ffdoc._i = i
        return self._ffdoc._w

    def __exit__(self, exc_type, exc_value, traceback):
        if self._ffdoc._w is not None:
            try:
                for _ in self._ffdoc._i:
                    pass
            finally:
                self._ffdoc._w = None
                self._ffdoc._i = False
                self._ffdoc._p = False

class WithXmlElement:
    """
    'With' statement context manager returned by `FlowFileDocument:getXmlMetadata`
    for accessing the XML metadata root `XmlElement`

    #### Usage
    ````
    with doc.getXmlMetadata() as xml:
        # Read or modify the XML metadata via the given root `XmlElement`
    ````
    """
    __slots__ = (
        '_ffdoc', '_node')
    def __init__(self, ffdoc, node):
        self._ffdoc = ffdoc
        self._node = node

    def __enter__(self) -> XmlElement:
        return self._node

    def __exit__(self, exc_type, exc_value, traceback):
        if self._ffdoc._w is None and self._ffdoc._p is not True:
            _i.FlowFileDocument_updateAttributes(self._ffdoc._c, DocumentModifier())

class FlowFileDocument:
    """
    The FlowFileDocument class

    Modifications to a FlowFileDocument can be performed efficiently using access methods
    `FlowFileDocument.modifying`, `FlowFileDocument.modify`, `FlowFileDocument.partsModify`
    and similar more restrictive variants in this class.

    Modifications are performed via various action sub-classes of `DocumentAction` provided
    by the access methods.

    `DocumentAction` itself can be used to access the attributes and XML metadata of
    the FlowFileDocument and to add new text content and file parts to the document.
    The various sub-classes act on specific part types to provide operations for
    those specific parts.

    A few convenience methods are available for accessing attributes, XML metadata and
    all content-text parts.  Be aware that such methods may be less efficient and result
    in more IO operations when combined together, compared to using the access methods
    to manage the underlying FlowFile access.
    """
    __slots__ = (
        '_c','_w','_i','_p')
    def __init__(self, capsule):
        """@private"""
        self._c = capsule
        self._w = None
        self._i = False
        self._p = False

    def getFilenameCount(self) -> int:
        """
        #### Returns
        The number of parts of the document referencing files on the filesystem
        """
        return _i.FlowFileDocument_getFilenameCount(self._c)

    def getExternalFileCount(self) -> int:
        """
        #### Returns
        The number of parts of the document referencing files stored externally
        """
        return _i.FlowFileDocument_getExternalFileCount(self._c)

    def getFileCount(self) -> int:
        """
        #### Returns
        The number of parts of the document that embed a file
        """
        return _i.FlowFileDocument_getFileCount(self._c)

    def getReference(self) -> str:
        """
        #### Returns
        The document reference (idol.reference attribute)
        """
        return _i.FlowFileDocument_getReference(self._c)

    def getReferenceAction(self) -> str:
        """
        #### Returns
        The document reference action (idol.reference.action attribute)

        Typically one of 'Add', 'Update' or 'Remove'
        """
        return _i.FlowFileDocument_getReferenceAction(self._c)

    def getAttribute(self, name:str, defValue:str = None) -> str:
        """
        Get a FlowFile attribute by name

        <div class="tip" markdown="1">Part attributes are excluded, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        * defValue (str): Default value

        #### Returns
        The attribute value or the provided default if the attribute does not exist
        """
        return _i.FlowFileDocument_getAttribute(self._c, name, defValue)

    def getAttributes(self) -> dict[str,str]:
        """
        Get a dictionary of all FlowFile attributes

        <div class="tip" markdown="1">Part attributes are excluded, they should be accessed through part operations</div>

        #### Returns
        A dictionary of all FlowFile attributes
        """
        return _i.FlowFileDocument_getAttributes(self._c)

    def setAttribute(self, name:str, value:str):
        """
        Set a FlowFile attribute

        <div class="tip" markdown="1">Part attributes are ignored, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        * value (str): Attribute value
        """
        return _i.FlowFileDocument_setAttribute(self._c, name, value)

    def removeAttribute(self, name:str):
        """
        Remove a FlowFile attribute

        <div class="tip" markdown="1">Part attributes are ignored, they should be accessed through part operations</div>

        #### Parameters
        * name (str): Attribute name
        """
        _i.FlowFileDocument_removeAttribute(self._c, name)

    def getXmlMetadata(self, native:bool = True) -> WithXmlElement:
        """
        Get the XML metadata for the document, when used in a 'with' statement

        The native parameter can usually be ignored, and may only be beneficial for optimization

        <div class="tip" markdown="1">The XML metadata can also be accessed via a `DocumentAction`</div>

        #### Parameters
        * native (bool): True to use native implementation, False for Java implementation

        #### Returns
        A `WithXmlElement` for use in a 'with' statement to access the root element `XmlElement`

        #### Usage
        Performing operations only on the metadata
        ````
        with doc.getXmlMetadata() as xml:
            # Read or modify the XML metadata via the given root `XmlElement`
        ````

        Alternatively using `FlowFileDocument.modifying` for full document access:
        ````
        with doc.modifying() as action:
            xml = action.getXmlMetadata()
            # Read or modify the whole document, including the XML metadata
        ````
        """
        return WithXmlElement(self, _i.FlowFileDocument_getXmlMetadata(self._c, native))

    def getXmlMetadataString(self) -> str:
        """
        #### Returns
        The XML metadata for the document as a plain XML string
        """
        return _i.FlowFileDocument_getXmlMetadataString(self._c)

    def setXmlMetadataString(self, xmlMetadata:str):
        """
        Replace the document XML metadata with the plain XML string provided

        <div class="tip" markdown="1">The XML metadata can be updated directly via the XmlElement returned by `FlowFileDocument.getXmlMetadata`</div>

        #### Parameters
        * xmlMetadata (str): The new XML metadata string
        """
        _i.DocumentAction_setXmlMetadataString(self._c, xmlMetadata)
        if self._w is None and self._p is not True:
            _i.FlowFileDocument_updateAttributes(self._c, DocumentModifier())

    def clearXmlMetadata(self):
        """
        Clear all elements from the XML metadata
        """
        _i.DocumentAction_clearXmlMetadata(self._c)
        if self._w is None and self._p is not True:
            _i.FlowFileDocument_updateAttributes(self._c, DocumentModifier())

    def _checkp(self, wda, callable):
        if self._p is True:
            if self._w is not None and wda is not None:
                self._w.restart(wda)
            else:
                raise RuntimeError('FlowFileDocument operations already in progress')
        try:
            if self._i is False:
                self._p = True
            callable()
        finally:
            if self._i is False:
                self._p = False

    def appending(self) -> WithDocumentAction:
        """
        #### Returns
        'With' statement context manager `WithDocumentAction` for append operations

        #### Usage
        ````
        with doc.appending() as action:
            # Read from the `FlowFileDocument`, update attribute and metadata, and append file or content parts
        ````
        """
        return WithDocumentAction(self, self.append)

    def append(self, modifier:DocumentModifier|DocMod|Callable[[DocumentAction],None]):
        """
        Append file or content parts to the document

        A `DocumentModifier` or `DocMod` or a callable accepting a `DocumentAction` should be passed to this function.
        The modifiers can be used to access existing parts.
        The modifiers or the callable can be used to access attributes and XML metadata,
        and append new parts or modify the attributes and XML metadata.

        #### Parameters
        * modifier (`DocumentModifier`|`DocMod`|Callable): A Modifier or a callable accepting a `DocumentAction`
        """
        self._checkp(self.appending(), lambda:
            _i.FlowFileDocument_append(self._c, DocumentModifier(modifier) if isinstance(modifier, DocMod) else modifier)
        )

    def reading(self) -> WithDocumentAction:
        """
        #### Returns
        'With' statement context manager `WithDocumentAction` for read operations

        #### Usage
        ````
        with doc.reading() as action:
            # Read from the `FlowFileDocument`
        ````
        """
        return WithDocumentAction(self, self.read)

    def read(self, modifier:DocumentModifier|DocMod|Callable[[DocumentAction],None]):
        """
        Read the document parts and data

        A `DocumentModifier` or `DocMod` or a callable accepting a `DocumentAction` should be passed to this function.
        The modifiers can be used to read existing parts.
        The modifiers or the callable can be used to read attributes and XML metadata.
        All write operations are disabled and result in an error.

        #### Parameters
        * modifier (`DocumentModifier`|`DocMod`|Callable): A Modifier or a callable accepting a `DocumentAction`
        """
        self._checkp(self.reading(), lambda:
            _i.FlowFileDocument_read(self._c, DocumentModifier(modifier) if isinstance(modifier, DocMod) else modifier)
        )

    def updatingAttributes(self) -> WithDocumentAction:
        """
        #### Returns
        'With' statement context manager `WithDocumentAction` for attribute and metadata update operations

        #### Usage
        ````
        with doc.updatingAttributes() as action:
            # Read from the `FlowFileDocument`, and update attributes and metadata
        ````
        """
        return WithDocumentAction(self, self.updateAttributes)

    def updateAttributes(self, modifier:DocumentModifier|DocMod|Callable[[DocumentAction],None]):
        """
        Update attributes and XML metadata of the document

        A `DocumentModifier` or `DocMod` or a callable accepting a `DocumentAction` should be passed to this function.
        The modifiers can be used to read existing parts.
        The modifiers or the callable can be used to read attributes and XML metadata.
        The attributes and XML metadata may be modified, all other write operations are disabled and result in an error.

        #### Parameters
        * modifier (`DocumentModifier`|`DocMod`|Callable): A Modifier or a callable accepting a `DocumentAction`
        """
        self._checkp(self.updatingAttributes(), lambda:
            _i.FlowFileDocument_updateAttributes(self._c, DocumentModifier(modifier) if isinstance(modifier, DocMod) else modifier)
        )

    def modifying(self) -> WithDocumentAction:
        """
        #### Returns
        'With' statement context manager `WithDocumentAction` for modify operations

        #### Usage
        ````
        with doc.modifying() as action:
            # Read and modify the `FlowFileDocument`
        ````
        """
        return WithDocumentAction(self, self.modify)

    def modify(self, modifier:DocumentModifier|DocMod|Callable[[DocumentAction],None]):
        """
        Modify the document

        A `DocumentModifier` or `DocMod` or a callable accepting a `DocumentAction` should be passed to this function.
        The modifiers can be used to read or write parts.
        The modifiers or the callable can be used to append parts, and read or modify attributes and XML metadata.

        #### Parameters
        * modifier (`DocumentModifier`|`DocMod`|Callable): A Modifier or a callable accepting a `DocumentAction`
        """
        self._checkp(self.modifying(), lambda:
            _i.FlowFileDocument_modify(self._c, DocumentModifier(modifier) if isinstance(modifier, DocMod) else modifier)
        )

    def overwriting(self) -> WithDocumentAction:
        """
        #### Returns
        'With' statement context manager `WithDocumentAction` for overwrite operations

        #### Usage
        ````
        with doc.overwriting() as action:
            # Read and overwrite the `FlowFileDocument`
        ````

        Alternatively using `FlowFileDocument.modifying`
        ````
        with doc.modifying() as action:
            for part in action.parts():
                part.deletePart()
            # Add new parts using action
        ````
        """
        return WithDocumentAction(self, self.overwrite)

    def overwrite(self, modifier:DocumentModifier|DocMod|Callable[[DocumentAction],None]):
        """
        Overwrite all the file or content parts of the document

        A `DocumentModifier` or `DocMod` or a callable accepting a `DocumentAction` should be passed to this function.
        The modifiers can be used to read the original parts and write the replacement parts.
        The modifiers or the callable can be used to write new parts, or read and write the attributes and XML metadata.

        #### Parameters
        * modifier (`DocumentModifier`|`DocMod`|Callable): A Modifier or a callable accepting a `DocumentAction`
        """
        self._checkp(self.overwriting(), lambda: 
            _i.FlowFileDocument_overwrite(self._c, DocumentModifier(modifier) if isinstance(modifier, DocMod) else modifier)
        )

    def compact(self, unwrapSinglePart:bool):
        """
        Compact the document by removing unused parts and optionally unwrapping the document if it only contains a single part to just the part data

        The use of unwrapSinglePart=True, when a single part is present, will also update the idol.type and mime.type attributes to match.
        If the document is subsequently modified by another processor that reads FlowFileDocuments, it may be restored to the full FlowFileDocument format.

        #### Parameters
        * unwrapSinglePart (bool): True to unwrap documents containing a single part
        """
        self._checkp(None, lambda:
            _i.FlowFileDocument_compact(self._c, unwrapSinglePart)
        )

    def _parts(self, wda) -> Generator[DocumentAction]:
        if self._p is True:
            if self._w is not None:
                self._w.restart(wda)
            else:
                raise RuntimeError('FlowFileDocument operations already in progress')
        if self._i is not True and self._i is not False:
            if self._w is None:
                raise RuntimeError('FlowFileDocument operations already in progress')
            self._p = True
            action = next(self._i, None)
            while (action is not None and type(action) != DocumentAction):
                yield action
                action = next(self._i, None)
            return
        if self._w is not None:
            raise RuntimeError('FlowFileDocument operations already in progress')
        try:
            def modifyThreadFn(ffdoc, modifierMethod, cond):
                with cond:
                    try:
                        class ModifyPartsDocMod(DocMod):
                            def preAction(self, action:DocumentAction):
                                if ffdoc._i is False:
                                    ffdoc._p = True
                                if ffdoc._i is True and cond.action is not False:
                                    cond.action = action
                                    cond.notify()
                                    cond.wait()
                            def onContent(self, action:ContentAction):
                                if cond.action is not False:
                                    cond.action = action
                                    cond.notify()
                                    cond.wait()
                            def defaultFileAction(self, action:FileAction):
                                if cond.action is not False:
                                    cond.action = action
                                    cond.notify()
                                    cond.wait()
                            def postAction(self, action:DocumentAction):
                                if ffdoc._i is not True and ffdoc._i is not False and cond.action is not False:
                                    cond.action = action
                                    cond.notify()
                                    cond.wait()
                        modifierMethod(ModifyPartsDocMod())
                    except Exception as e:
                        cond.ex = e
                    finally:
                        cond.action = False
                        cond.notify()
            cond = Condition()
            cond.action = True
            cond.ex = None
            with cond:
                _tp_exec(target=modifyThreadFn, args=(self, wda._mod, cond))
                cond.wait()
                try:
                    while cond.action is not False:
                        yield cond.action
                        cond.notify()
                        cond.wait()
                finally:
                    cond.action = False
                    cond.notify()
            if cond.ex is not None:
                raise cond.ex
        finally:
            if self._i is False:
                self._p = False

    def partsModify(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A Generator for looping over the parts of a `FlowFileDocument` for modification

        #### Usage
        ````
        for part in doc.partsModify():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            elif part.isFilePart():
                logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Modify any of the parts or the document
        ````

        Alternatively using `FlowFileDocument.modifying`
        ````
        with doc.modifying() as action:
            for part in action.parts():
                if part.isContentPart():
                    logInfo("Content part", part.getPartId())
                elif part.isFilePart():
                    logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
                # Modify any of the parts or the document
        ````
        """
        return self._parts(self.modifying())

    def partsOverwrite(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A Generator for looping over the parts of a `FlowFileDocument` for reading and completely overwriting

        #### Usage
        ````
        for part in doc.partsOverwrite():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            elif part.isFilePart():
                logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Read parts and overwrite by explicitly rewriting the parts or by adding new parts
        ````

        Alternatively using `FlowFileDocument.modifying`
        ````
        with doc.overwriting() as action:
            for part in action.parts():
                if part.isContentPart():
                    logInfo("Content part", part.getPartId())
                elif part.isFilePart():
                    logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
                # Read parts and overwrite by explicitly rewriting the parts or by adding new parts
        ````
        """
        return self._parts(self.modifying())

    def partsAppend(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A Generator for looping over the parts of a `FlowFileDocument` for appending parts and updating attribute and metadata

        #### Usage
        ````
        for part in doc.partsAppend():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            elif part.isFilePart():
                logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Read parts and append replacement parts or new parts
        ````

        Alternatively using `FlowFileDocument.appending`
        ````
        with doc.appending() as action:
            for part in action.parts():
                if part.isContentPart():
                    logInfo("Content part", part.getPartId())
                elif part.isFilePart():
                    logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
                # Read parts and append replacement parts or new parts
        ````
        """
        return self._parts(self.appending())

    def partsUpdateAttributes(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A Generator for looping over the parts of a `FlowFileDocument` for attribute and metadata updates

        #### Usage
        ````
        for part in doc.partsUpdateAttributes():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            elif part.isFilePart():
                logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Read and update part or document attributes or metadata
        ````

        Alternatively using `FlowFileDocument.updatingAttributes`
        ````
        with doc.updatingAttributes() as action:
            for part in action.parts():
                if part.isContentPart():
                    logInfo("Content part", part.getPartId())
                elif part.isFilePart():
                    logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
                # Read and update part or document attributes or metadata
        ````
        """
        return self._parts(self.updatingAttributes())

    def partsRead(self) -> Generator[DocumentAction]:
        """
        #### Returns
        A Generator for looping over the parts of a `FlowFileDocument` for reading

        #### Usage
        ````
        for part in doc.partsRead():
            if part.isContentPart():
                logInfo("Content part", part.getPartId())
            elif part.isFilePart():
                logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Read any of the parts or the document
        ````

        Alternatively using `FlowFileDocument.reading`
        ````
        with doc.reading() as action:
            for part in action.parts():
                if part.isContentPart():
                    logInfo("Content part", part.getPartId())
                elif part.isFilePart():
                    logInfo("File (" + type(part).__name__ + ") part " + part.getPartId())
            # Read any of the parts or the document
        ````
        """
        return self._parts(self.reading())

    def getContentPages(self) -> Generator[str]:
        """
        #### Returns
        A Generator for reading all the content text pages of a `FlowFileDocument`

        #### Usage
        ````
        for content in doc.getContentPages():
            # Use content string
        ````

        Alternatively using `FlowFileDocument.reading`
        ````
        with doc.reading() as action:
            for part in action.parts():
                if part.isContentPart():
                    content = part.getContent()
                    # Use content string
        ````
        """
        for part in self.partsRead():
            if part.isContentPart():
                yield from part.getContent()

    def deleteContentPages(self):
        """
        Delete all content text pages from the `FlowFileDocument`

        #### Usage
        ````
        doc.deleteContentPages()
        ````

        Alternatively using `FlowFileDocument.modifying`
        ````
        with doc.modifying() as action:
            for part in action.parts():
                if part.isContentPart():
                    part.deletePart()
        ````
        """
        for part in self.partsModify():
            if part.isContentPart():
                part.deletePart()

    def setContentPages(self, contentStreamer:list[str]|str|InputStream|IOBase|Callable[[TextOutputStream],None]):
        """
        Replaces all the content parts and pages in the `FlowFileDocument` with
        a single part containing the pages provided

        #### Parameters
        * contentStreamer (str|InputStream|IOBase|Callable): The content string, input stream or stream writer

        #### Usage
        ````
        doc.setContentPages('My single content page')
        ````

        Alternatively using `FlowFileDocument.modifying`
        ````
        with doc.modifying() as action:
            for part in action.parts():
                if part.isContentPart():
                    part.deletePart()
            action.addContent('My single content page')
        ````
        """
        if self._w is not None:
            self.deleteContentPages()
            self._w.addContent(contentStreamer)
        else:
            with self.modifying() as action:
                self.deleteContentPages()
                action.addContent(contentStreamer)

    def getAsFlowFile(self) -> FlowFile:
        """
        #### Returns
        The underlying `FlowFile` for this document

        <div class="warn" markdown="1">This does not guarantee that modifications have been applied.
            The `FlowFile` should not be committed, or other operations performed directly on it 
            or via the `ProcessSession` while any `FlowFileDocument` operations are in progress.</div>
        """
        return _i.FlowFileDocument_getAsFlowFile(self._c)
