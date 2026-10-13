---@meta

-- BEGIN COPYRIGHT NOTICE
-- Copyright 2026 Open Text.
--
-- The only warranties for products and services of Open Text and its affiliates and licensors
-- ("Open Text") are as may be set forth in the express warranty statements accompanying such
-- products and services. Nothing herein should be construed as constituting an additional warranty.
-- Open Text shall not be liable for technical or editorial errors or omissions contained herein.
-- The information contained herein is subject to change without notice.
--
-- END COPYRIGHT NOTICE

-- Type aliases ----------------------------------------------

---@alias acirequest_getparam_consumer fun(p1: LuaInputStream, p2: table<string, string>)
---@alias document_handler_function fun(p1: LuaDocument)
---@alias flowfile_list LuaFlowFile[]
---@alias flowfiledocument_or_flowfile LuaFlowFileDocument|LuaFlowFile
---@alias hash_file_bytes_function fun(): string?
---@alias inputstream_function fun(p1: LuaInputStream)
---@alias inputstream_outputstream_function fun(p1: LuaInputStream, p2: LuaOutputStream)
---@alias json_array_ipairs_next_function fun(p1: LuaJsonArray, p2: integer?): integer?, LuaJsonValue?
---@alias json_object_pairs_next_function fun(p1: LuaJsonObject, p2: string?): string?, LuaJsonValue?
---@alias json_path_string_or_integer integer|string
---@alias lua_config_value boolean|integer|string
---@alias lua_json_object_type table<string, lua_json_value_type>
---@alias lua_json_simple_type nil|boolean|number|integer|string
---@alias lua_json_type nil|boolean|number|integer|string|LuaJsonObject|LuaJsonArray
---@alias lua_json_value_type nil|boolean|number|integer|string|LuaJsonObject|LuaJsonArray|LuaJsonValue
---@alias modify_action_function fun(p1: LuaModifyAction)
---@alias modify_content_action_function fun(p1: LuaModifyContentAction)
---@alias modify_content_file_action_function fun(p1: LuaModifyContentFileAction)
---@alias modify_content_filename_action_function fun(p1: LuaModifyContentFilenameAction)
---@alias modify_external_file_action_function fun(p1: LuaModifyExternalFileAction)
---@alias modify_file_action_function fun(p1: LuaModifyFileAction)
---@alias modifydocument_handler_function fun(p1: LuaDocument): modifydocument_handler_return...
---@alias modifydocument_handler_return LuaDocument|LuaFlowFileDocument|LuaFlowFile|boolean|nil
---@alias modifyflowfiledocument_handler_function fun(p1: LuaFlowFileDocument): modifyflowfiledocument_handler_return...
---@alias modifyflowfiledocument_handler_return LuaFlowFileDocument|LuaFlowFile|boolean|nil
---@alias numeric_or_string number|integer|string
---@alias optional_string_table table<string, string>?
---@alias outputstream_function fun(p1: LuaOutputStream)
---@alias outputstream_function_or_inputstream outputstream_function|LuaInputStream
---@alias outputstream_function_or_inputstream_or_string outputstream_function|LuaInputStream|string
---@alias string_consumer_function fun(p1: string)
---@alias string_to_string_function fun(p1: string): string
---@alias xml_node_set_ipairs_next_function fun(p1: LuaXmlNodeSet, p2: integer?): integer?, LuaXmlNode?

-- Named parameter groups -----------------------------------

---@class modify_named_parameters
---@field defaultFileAction modify_file_action_function Function taking a single LuaModifyFileAction argument. Used as the default for onContentFile, onContentFilename and onExternalFile
---@field onContent modify_content_action_function Function taking a single LuaModifyContentAction argument
---@field onContentFile modify_content_file_action_function Function taking a single LuaModifyContentFileAction argument
---@field onContentFilename modify_content_filename_action_function Function taking a single LuaModifyContentFilenameAction argument
---@field onExternalFile modify_external_file_action_function Function taking a single LuaModifyExternalFileAction argument
---@field postAction modify_action_function Function taking a single LuaModifyAction argument
---@field preAction modify_action_function Function taking a single LuaModifyAction argument

---@class parse_document_csv_named_parameters
---@field base_reference? string If there is no reference field, then use this as the base reference with line number appended (default: )
---@field content_field? string Field to use as content (default: DRECONTENT)
---@field csv_field_names string[] List of names for CSV file fields. This overrides any header line if present
---@field map_all_to_content? boolean Map every column in to the drecontent, newline separated (default: false)
---@field reference_field? string Field to use as reference (default: DREREFERENCE)
---@field use_header_row? boolean Specify false if the CSV file does not include a header line (default: true)

---@class parse_document_xml_named_parameters
---@field content_paths string[] Paths representing the content elements within a document
---@field document_root_paths string[] Paths representing the root element of a document
---@field include_root_path? boolean True to include root path in metadata, false to only include children of the root (default: false)
---@field reference_paths string[] Paths representing the reference element within a document, there must be exactly one reference identified per document

---@class send_http_request_named_parameters
---@field content string For http POST, the content to be sent with the post request.
---@field headers table<string, string> Any http headers that need to be sent with the request
---@field host string The hostname (say, google.com) to which to send the http request.
---@field method? string The http method to be used. Valid values are GET, POST and DELETE. (default: GET)
---@field options optional_string_table Configuration options (SSL, proxy, authentication) to use instead of requiring application config
---@field params table<string, string> Extra parameters for the request.
---@field port? integer The port to which to send the http request. (default: 80)
---@field section? string The name of the config section for lookup of transport-related parameters such as SSL or proxy settings. (default: default)
---@field uri string The uri to request.
---@field url string The full url for the http request. If provided, the other parameters normally used to build up the url in parts are not used.

-- ===========================================================
-- Module: ExecuteDocumentLua functionality
-- ===========================================================

---ACI Request class
---@class LuaAciRequest
local LuaAciRequest = {}

---Get the action name
---@return string # Action name
function LuaAciRequest:getAction() end

---Get a parameter
---@param name string Parameter name
---@param consumer acirequest_getparam_consumer Consumer function with data from LuaInputStream and optional header table
---@return string? # Parameter value as a string if a consumer function is not provided
---@overload fun(name: string): string?
function LuaAciRequest:getParam() end

---Get the parameter value parsed as XML
---@param name string Parameter name
---@return LuaXmlMetadataElement # Parameter value parsed as XML
function LuaAciRequest:getParamAsXml() end

---Get the parameter names
---@return string[] # List of parameter names
function LuaAciRequest:getParamNames() end

---Get the parameter names
---@param name string Parameter name
---@return string # Parameter source type (one of 'multipart', 'attribute' or 'none')
function LuaAciRequest:getParamSource() end

---Get the parameter source types for all parameters
---@return table<string, string> # Mapping from parameter names to parameter source type (either 'multipart' or 'attribute')
function LuaAciRequest:getParamSources() end

---Get the action token
---@return string # Action token
function LuaAciRequest:getToken() end

---Returns true if the action is synchronous
---@return bool # true if synchronous
function LuaAciRequest:isSynchronous() end

---FlowFile class
---@class LuaFlowFile : LuaFlowFileCommon
local LuaFlowFile = {}

---Returns a LuaAciRequestReader for this FlowFile
---@return LuaAciRequest # ACI request
function LuaFlowFile:getAsAciRequest() end

---Returns a LuaFlowFileDocument for this FlowFile
---@return LuaFlowFileDocument # FlowFile Document
function LuaFlowFile:getAsFlowFileDocument() end

---Modify the FlowFile using a LuaFlowFileDocument handler function.
---@param flowfileDocumentHandler modifyflowfiledocument_handler_function Function taking a single LuaFlowFileDocument argument, and may return multiple LuaDocument, LuaFlowFileDocument, LuaFlowFile, boolean or nil values
---@return modifyflowfiledocument_handler_return ... # Results of document handler, as multiple LuaFlowFileDocuments or LuaFlowFiles with the LuaFlowFileDocument input replaced by this LuaFlowFile if it is also returned. Boolean or nil may also be returned
function LuaFlowFile:modifyFlowFileDocument() end

---Read the FlowFile
---@param reader inputstream_function Function taking input stream
function LuaFlowFile:readFlowFile() end

---Transform the FlowFile
---@param readerWriter inputstream_outputstream_function Function taking input stream and output stream
function LuaFlowFile:transformFlowFile() end

---Write the FlowFile
---@param writer outputstream_function_or_inputstream Function taking output stream, or an inputstream to read the data from
function LuaFlowFile:writeFlowFile() end

---FlowFile base class
---@class LuaFlowFileCommon
local LuaFlowFileCommon = {}

---Get an attribute from the FlowFile
---@param name string Name of the attribute to retrieve
---@param def? string Optional default value
---@return string? # Value of the attribute or nil
function LuaFlowFileCommon:getAttribute() end

---Get the attributes from the FlowFile
---@return table<string, string> # Table of attributes
function LuaFlowFileCommon:getAttributes() end

---Remove an attribute from the FlowFile
---@param name string Name of the attribute to remove
function LuaFlowFileCommon:removeAttribute() end

---Remove attributes from the FlowFile
---@param attributes string[] List of attributes to remove
function LuaFlowFileCommon:removeAttributes() end

---Set an attribute on the FlowFile
---@param name string Name of the attribute to set
---@param value string Value of the attribute
function LuaFlowFileCommon:setAttribute() end

---Set attributes on the FlowFile
---@param attributes table<string, string> Table of attributes to set
function LuaFlowFileCommon:setAttributes() end

---FlowFile document class
---@class LuaFlowFileDocument : LuaFlowFileCommon
local LuaFlowFileDocument = {}

---Append to the document. All modifications are appended to the FlowFile, including marking an existing part for removal if necessary
---@param action modify_action_function Function taking a single LuaModifyAction argument
---@overload fun(params: modify_named_parameters)
function LuaFlowFileDocument:append() end

---Compact the document to strip out parts that have been removed
---@param unwrapSinglePart bool Unwrap documents containing a single part
function LuaFlowFileDocument:compact() end

---Return the LuaFlowFile for this document
---@return LuaFlowFile # FlowFile
function LuaFlowFileDocument:getAsFlowFile() end

---Create a LuaDocument object containing the text content and metadata from the FlowFile document
---@return LuaDocument # Document
function LuaFlowFileDocument:getAsLuaDocument() end
function LuaFlowFileDocument:getAsDocument() end

---Get the count of ExternalFile parts in the document
---@return integer # Count of ExternalFile parts in document
function LuaFlowFileDocument:getExternalFileCount() end

---Get the count of file parts in the document
---@return integer # Count of file parts in document
function LuaFlowFileDocument:getFileCount() end

---Get the count of filename parts in the document
---@return integer # Count of filename parts in document
function LuaFlowFileDocument:getFilenameCount() end

---Get the idol.reference attribute
---@return string # Reference
function LuaFlowFileDocument:getReference() end

---Get the idol.reference.action attribute
---@return string # Reference action
function LuaFlowFileDocument:getReferenceAction() end

---Modify the document. Will always results in the FlowFile being rewritten
---@param action modify_action_function Function taking a single LuaModifyAction argument
---@overload fun(params: modify_named_parameters)
function LuaFlowFileDocument:modify() end

---Modify the document using a LuaDocument handler function. Will always result in the FlowFile being rewritten
---@param documentHandler modifydocument_handler_function Function taking a single LuaDocument argument, and may return multiple LuaDocument, LuaFlowFileDocument, boolean or nil values
---@return modifydocument_handler_return ... # Results of document handler, as multiple LuaDocument or LuaFlowFileDocuments with the LuaDocument input replaced by this LuaFlowFileDocument if it is also returned. Boolean or nil may also be returned
function LuaFlowFileDocument:modifyDocument() end

---Overwrite the document. The entire existing body of the FlowFile is discarded, and new parts added
---@param action modify_action_function Function taking a single LuaModifyAction argument
---@overload fun(params: modify_named_parameters)
function LuaFlowFileDocument:overwrite() end

---Read the document. Write operations are disabled and will not work
---@param action modify_action_function Function taking a single LuaModifyAction argument
---@overload fun(params: modify_named_parameters)
function LuaFlowFileDocument:read() end

---Populate the reference, metadata and text content from a LuaDocument
---@param document LuaDocument Document
function LuaFlowFileDocument:setFromLuaDocument() end

---Read the document and modify attributes or metadata. Write operations for files and content are disabled and will not work
---@param action modify_action_function Function taking a single LuaModifyAction argument
---@overload fun(params: modify_named_parameters)
function LuaFlowFileDocument:updateAttributes() end

---Input stream
---@class LuaInputStream
local LuaInputStream = {}

---Construct an input stream for an existing file
---@param filename string Filename to open
---@return LuaInputStream
function LuaInputStream.new(filename) end

---Read formatted values from stream, defaults to read a line if no formats specified
---@param formats numeric_or_string ... Read formats ['n'(number), 'l'(line), 'L'(line with end-of-line), 'a'(all), number of bytes]
---@return numeric_or_string ... # Values read from stream
function LuaInputStream:read() end

---Flow file document modify document action class
---@class LuaModifyAction
local LuaModifyAction = {}

---Add content to the document; pages may be separated by a page break character 12 (0x0C)
---@param content outputstream_function_or_inputstream_or_string Function taking output stream to write to, or an input stream to read from, or a string for a whole page or multiple pages of content
---@return LuaModifyPartAction # Action class to allow metadata or attributes to be modified for the part
function LuaModifyAction:addContent() end

---Add an external file part to the document
---@param locatorJavaClassAndServiceKey string Locator Java class (ClassName or #ServiceKey or ClassName#ServiceKey)
---@param locatorProperties table<string, string> Locator file location properties
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
---@param mimeType? string File mime-type
---@return LuaModifyFilePartAction # Action class to allow metadata or attributes to be modified for the file
function LuaModifyAction:addExternalFile() end

---Add an file content part to the document
---@param file outputstream_function_or_inputstream Function taking output stream to write to, or an input stream to read from
---@param displayFilename? string Display filename
---@param mimeType? string File mime-type
---@return LuaModifyFilePartAction # Action class to allow metadata or attributes to be modified for the file
function LuaModifyAction:addFile() end

---Add a filename part to the document
---@param filename string Filename
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
---@param mimeType? string File mime-type
---@return LuaModifyFilePartAction # Action class to allow metadata or attributes to be modified for the file
function LuaModifyAction:addFilename() end

---Clear the XML metadata stored with the document
function LuaModifyAction:clearXmlMetadata() end

---Delete file on processor session commit
---@param filename string Filename
function LuaModifyAction:deleteFileOnCommit() end

---Delete file on processor session rollback
---@param filename string Filename
function LuaModifyAction:deleteFileOnRollback() end

---Returns a FlowFile attribute
---@param name string Attribute name
---@param def? string Optional default value
---@return string? # Attribute value, default value or nil
function LuaModifyAction:getAttribute() end
function LuaModifyAction:getFlowFileAttribute() end

---Returns the FlowFile attributes
---@return table<string, string> # FlowFile attributes
function LuaModifyAction:getAttributes() end
function LuaModifyAction:getFlowFileAttributes() end

---Get the document XML metadata
---@return LuaXmlMetadataElement # 
function LuaModifyAction:getXmlMetadata() end

---Get the document XML metadata as an XML string
---@return string # 
function LuaModifyAction:getXmlMetadataString() end

---Remove a FlowFile attributes
---@param name string Attribute name
---@return LuaModifyAction # This class instance
function LuaModifyAction:removeAttribute() end
function LuaModifyAction:removeFlowFileAttribute() end

---Sets a FlowFile attributes
---@param name string Attribute name
---@param value string Attribute value
---@return LuaModifyAction # This class instance
function LuaModifyAction:setAttribute() end
function LuaModifyAction:setFlowFileAttribute() end

---Set the document XML metadata from an XML string
---@param xmlMetadata string Replacement XML Metadata string
function LuaModifyAction:setXmlMetadataString() end

---Flow file document modify content action class
---@class LuaModifyContentAction : LuaModifyPartAction
local LuaModifyContentAction = {}

---Read the content
---@param pageReader inputstream_function Function taking input stream
---@param wholePartConsumer boolean true for pageReader to be called once for whole part, false for one call per page in part
---@param readAndKeep boolean Should the part be rewritten unmodified after read
---@overload fun(pageReader: inputstream_function, readAndKeep?: boolean)
function LuaModifyContentAction:readContent() end

---Transform the content
---@param pageReadWriter inputstream_outputstream_function Function taking input stream and output stream
---@param wholePartConsumer? boolean true for pageReadWriter to be called once for whole part, false for one call per page in part (default: false)
function LuaModifyContentAction:transformContent() end

---Write the content
---@param contentWriter outputstream_function Function taking output stream
function LuaModifyContentAction:writeContent() end

---Flow file document modify content file action class
---@class LuaModifyContentFileAction : LuaModifyFileAction
local LuaModifyContentFileAction = {}

---Write the file
---@param writer outputstream_function Function taking output stream
function LuaModifyContentFileAction:writeFile() end

---Flow file document modify content filename action class
---@class LuaModifyContentFilenameAction : LuaModifyFileAction
local LuaModifyContentFilenameAction = {}

---Disown the file
function LuaModifyContentFilenameAction:disownFilename() end
function LuaModifyContentFilenameAction:disownFile() end

---Returns whether this file exists
---@return bool # Returns true if the file exists
function LuaModifyContentFilenameAction:exists() end

---Get the filename referenced by the part
---@return string # The filename
function LuaModifyContentFilenameAction:getFilename() end

---Returns whether this has ownership of the file
---@return bool # Returns true if have ownership of the file; if true, the file would be deleted when the removal of the file from the document is committed
function LuaModifyContentFilenameAction:hasFilenameOwnership() end
function LuaModifyContentFilenameAction:hasOwnership() end

---Replace the stored filename with a different filename; if the old filename was owned by this, it would be deleted on commit
---@param filename string Filename
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
function LuaModifyContentFilenameAction:replaceFilename() end

---Flow file document modify external file action class
---@class LuaModifyExternalFileAction : LuaModifyFileAction
local LuaModifyExternalFileAction = {}

---Disown the external file
function LuaModifyExternalFileAction:disownFile() end

---Returns whether this file exists
---@return bool # Returns true if the file exists
function LuaModifyExternalFileAction:exists() end

---Get a download URL for the file if supported; this may be a signed time-limited URL
---@return string? # The download URL for the file, or nil
function LuaModifyExternalFileAction:getDownloadUrl() end

---Get the locator Java class name referenced by the part
---@return string # The external file locator Java class name
function LuaModifyExternalFileAction:getLocatorJavaClass() end

---Get the locator Java class name and service key referenced by the part, in the format 'ClassName' or '#ServiceKey' or 'ClassName#ServiceKey'
---@return string # The external file locator Java class name and service key
function LuaModifyExternalFileAction:getLocatorJavaClassAndServiceKey() end

---Get the locator file location properties referenced by the part
---@return table<string, string> # The external file locator file location properties
function LuaModifyExternalFileAction:getLocatorProperties() end

---Get the locator Java service key referenced by the part
---@return string # The external file locator service key
function LuaModifyExternalFileAction:getLocatorServiceKey() end

---Returns whether this has ownership of the external file
---@return bool # Returns true if have ownership of the external file; if true, the external file would be deleted when the removal of the file from the document is committed
function LuaModifyExternalFileAction:hasOwnership() end

---Replace the stored external file with a different external file; if the old external file was owned by this, it would be deleted on commit
---@param locatorJavaClassAndServiceKey string Output locator Java class (ClassName or #ServiceKey or ClassName#ServiceKey)
---@param locatorProperties table<string, string> Output locator file location properties
---@param ownFile bool File ownership; if true, the external file would be deleted when the removal of the external file from the document is committed
function LuaModifyExternalFileAction:replaceLocator() end

---Flow file document modify file action class
---@class LuaModifyFileAction : LuaModifyFilePartAction
local LuaModifyFileAction = {}

---Read the file
---@param handler string_consumer_function Function taking a filename
---@param readAndKeep? boolean Should the part be rewritten unmodified after read (default: false)
function LuaModifyFileAction:readAsFilename() end

---Read the file
---@param reader inputstream_function Function taking input stream
---@param readAndKeep? boolean Should the part be rewritten unmodified after read (default: false)
function LuaModifyFileAction:readFile() end

---Transform to an external file part
---@param locatorJavaClassAndServiceKey string Output locator Java class (ClassName or #ServiceKey or ClassName#ServiceKey)
---@param locatorProperties table<string, string> Locator file location properties
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
---@param readerWriter? inputstream_outputstream_function Optional transform function taking input stream and output stream
function LuaModifyFileAction:transferToExternalFile() end

---Transform to a file part
---@param readerWriter? inputstream_outputstream_function Optional transform function taking input stream and output stream
function LuaModifyFileAction:transferToFile() end

---Transform to a filename part
---@param filename string output filename
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
---@param readerWriter? inputstream_outputstream_function Optional transform function taking input stream and output stream
function LuaModifyFileAction:transferToFilename() end

---Transform the file by filename to a new filename
---@param handler string_to_string_function Function taking a filename and returning a new filename
---@param ownFile bool File ownership; if true, the file would be deleted when the removal of the file from the document is committed
function LuaModifyFileAction:transformAsFilename() end

---Transform the file
---@param readerWriter inputstream_outputstream_function Function taking input stream and output stream
function LuaModifyFileAction:transformFile() end

---Flow file document modify file part action class
---@class LuaModifyFilePartAction : LuaModifyPartAction
local LuaModifyFilePartAction = {}

---Set the file display name
---@param displayName string File display name
---@return LuaModifyFilePartAction # This class instance
function LuaModifyFilePartAction:setFileDisplayName() end

---Set the file mime-type
---@param mimeType string File mime-type
---@return LuaModifyFilePartAction # This class instance
function LuaModifyFilePartAction:setFileMimeType() end

---Flow file document modify document part action class
---@class LuaModifyPartAction : LuaModifyAction
local LuaModifyPartAction = {}

---Delete this document part
function LuaModifyPartAction:deletePart() end

---Returns a document part attribute
---@param name string Attribute name
---@param def? string Optional default value
---@return string? # Attribute value, default value or nil
function LuaModifyPartAction:getPartAttribute() end

---Returns the document part attributes
---@return table<string, string> # Document part attributes
function LuaModifyPartAction:getPartAttributes() end

---Returns the document part ID
---@return string # Document part ID
function LuaModifyPartAction:getPartId() end
function LuaModifyPartAction:getPartUuid() end

---Get the document part XML metadata
---@return LuaXmlMetadataElement # 
function LuaModifyPartAction:getPartXmlMetadata() end

---Remove a document part attributes
---@param name string Attribute name
---@return LuaModifyPartAction # This class instance
function LuaModifyPartAction:removePartAttribute() end

---Sets a FlowFile attributes
---@param name string Attribute name
---@param value string Attribute value
---@return LuaModifyPartAction # This class instance
function LuaModifyPartAction:setPartAttribute() end

---Output stream
---@class LuaOutputStream
local LuaOutputStream = {}

---Write values to stream
---@param values numeric_or_string ... Values to write may be strings or numeric
function LuaOutputStream:write() end

---Processor session class
---@class LuaProcessorSession
local LuaProcessorSession = {}

---Returns the cluster state table for the processor
---@return table<string, string> # State table
function LuaProcessorSession:getClusterState() end

---Returns the local state table for the processor
---@return table<string, string> # State table
function LuaProcessorSession:getLocalState() end

---Returns the name of the processor
---@return string # Name of the processor
function LuaProcessorSession:getName() end

---Returns all known properties for the processor
---@return table<string, string> # Properties table
function LuaProcessorSession:getProperties() end

---Get a property value
---@param name string Name of the property to retrieve
---@param def? string Optional default value
---@return string? # Value of the property or nil
function LuaProcessorSession:getProperty() end

---Returns if there is a connection for the specified relationship
---@param relationship string Relationship name
---@return bool # Is relationship connected
function LuaProcessorSession:hasConnection() end

---Returns if there is available space on the connection for the specified relationship
---@param relationship string Relationship name
---@return bool # Is relationship available
function LuaProcessorSession:relationshipAvailable() end

---Set the cluster state table for the processor
---@param state table<string, string> State table
function LuaProcessorSession:setClusterState() end

---Set the local state table for the processor
---@param state table<string, string> State table
function LuaProcessorSession:setLocalState() end

---Evaluate an expression with the given attributes
---@param expression string Expression string
---@param attributes? table<string, string> Attributes
---@return string # Evaluated expression value
function LuaProcessorSession:evaluateAttributeExpressions() end

---Create a new empty LuaFlowFile
---@param parent? flowfiledocument_or_flowfile Parent LuaFlowFileDocument, LuaFlowFile or nil
---@return LuaFlowFile # New FlowFile
function LuaProcessorSession:createFlowFile() end

---Create a new empty LuaFlowFileDocument
---@param reference string idol.reference for new FlowFile
---@param referenceAction? string idol.reference.action for new FlowFile
---@param parent? flowfiledocument_or_flowfile parent LuaFlowFileDocument, LuaFlowFile or nil
---@return LuaFlowFileDocument # New FlowFile document
function LuaProcessorSession:create() end
function LuaProcessorSession:createFlowFileDocument() end

---Returns up to maxResults FlowFiles from the queue
---@param maxResults? integer The maximum number of FlowFiles to return (default: 1)
---@return flowfile_list # List of FlowFiles
function LuaProcessorSession:get() end

---Get the size of the incoming queue
---@return integer # Size of the incoming queue
function LuaProcessorSession:getQueueSize() end

---Remove a FlowFile from the flow
---@param flowFile flowfiledocument_or_flowfile LuaFlowFileDocument or LuaFlowFile
function LuaProcessorSession:remove() end

---Transfer a FlowFile to the specified relationship
---@param flowFile flowfiledocument_or_flowfile LuaFlowFileDocument or LuaFlowFile
---@param relationship? string Relationship name or nil to restore to incoming queue
function LuaProcessorSession:transfer() end

---XML metadata element
---@class LuaXmlMetadataElement
local LuaXmlMetadataElement = {}

---Add child element with name
---@param name string Element name
---@return LuaXmlMetadataElement # Child element
function LuaXmlMetadataElement:addChild() end

---Add child element from another element
---@param element LuaXmlMetadataElement Element to append
---@return LuaXmlMetadataElement # Child element
function LuaXmlMetadataElement:appendChild() end

---Get an attribute value
---@param name string Attribute name
---@param def? string Optional default value
---@return string? # Attribute value, default value or nil
function LuaXmlMetadataElement:getAttribute() end

---Get all attributes
---@return table<string, string> # Attributes
function LuaXmlMetadataElement:getAttributes() end

---Get child elements
---@return LuaXmlMetadataElement ... # Child elements
function LuaXmlMetadataElement:getChildren() end

---Get elements by XPath
---@param xpath string XPath
---@return LuaXmlMetadataElement ... # Elements
function LuaXmlMetadataElement:getElementsByXPath() end

---Get first child element with name
---@param name string Element name
---@return LuaXmlMetadataElement? # Child element
function LuaXmlMetadataElement:getFirstChild() end

---Get the element name
---@return string # Element name
function LuaXmlMetadataElement:getName() end

---Get or add child element with name
---@param name string Element name
---@return LuaXmlMetadataElement # Child element
function LuaXmlMetadataElement:getOrAddChild() end

---Get the element value
---@return string # Element value
function LuaXmlMetadataElement:getValue() end

---Get whether an attribute exists
---@param name string Attribute name
---@return bool # True if attribute exists
function LuaXmlMetadataElement:hasAttribute() end

---Remove this element
function LuaXmlMetadataElement:remove() end

---Remove an attribute value
---@param name string Attribute name
function LuaXmlMetadataElement:removeAttribute() end

---Set an attribute value
---@param name string Attribute name
---@param value string Attribute value
function LuaXmlMetadataElement:setAttribute() end

---Set the element value
---@param value string Element value
function LuaXmlMetadataElement:setValue() end

---Return the XML element as a string
---@return string # XML element as a string
function LuaXmlMetadataElement:toString() end

-- Global functions ------------------------------------------

---Gets the files storage directory for the processor. This can be used for temporary files or document files
---@return string # Files storage directory for the processor
function get_files_storage_directory() end

---Gets a temporary file path in the files storage directory
---@param prefix? string Temporary filename prefix (default: )
---@param extension? string Temporary filename extension (default: .tmp)
---@return string # Temporary file path
function get_temp_file() end

---Get NiFi log stream for processor
---@return LuaLog # The log object
function get_log() end

---Log a debug message to the NiFi log stream for the processor
---@param data any ... This is the message you want to log out
function log_debug() end

---Log an error message to the NiFi log stream for the processor
---@param data any ... This is the message you want to log out
function log_error() end

---Log an info message to the NiFi log stream for the processor
---@param data any ... This is the message you want to log out
function log_info() end

---Log a trace message to the NiFi log stream for the processor
---@param data any ... This is the message you want to log out
function log_trace() end

---Log a warning message to the NiFi log stream for the processor
---@param data any ... This is the message you want to log out
function log_warn() end

-- ===========================================================
-- Module: Standard functionality
-- ===========================================================

---Configuration class
---@class LuaConfig
local LuaConfig = {}

---Constructor for LuaConfig.
---@param config_buffer string The contents of the config.
---@return LuaConfig
function LuaConfig.new(config_buffer) end

---Read an encrypted config parameter.
---@param section string The config section name.
---@param key string The config parameter name.
---@return string # The config parameter value.
function LuaConfig:getEncryptedValue() end

---Read a config parameter.
---@param section string The config section name.
---@param key string The config parameter name.
---@param def lua_config_value The default value.
---@return lua_config_value # The config parameter value.
---@overload fun(section: string, key: string): lua_config_value
function LuaConfig:getValue() end

---Read a multivalued config parameter.
---@param section string The config section name.
---@param key string The config parameter name.
---@return string ... # The config parameter values.
function LuaConfig:getValues() end

---Document class
---@class LuaDocument : LuaFieldContainer
local LuaDocument = {}

---Constructor for LuaDocument.
---@param reference string The reference for the document.
---@return LuaDocument
function LuaDocument.new(reference) end

---Add a field.
---@param name string The field name.
---@param value string The field value.
---@return LuaField? # The new field.
---@overload fun(field: LuaField, name?: string): LuaField?
function LuaDocument:addField() end

---Add a new section to the document.
---@return LuaDocumentSection? # The newly added section.
function LuaDocument:addSection() end

---Append content.
---@param content string The new content.
---@param number? integer The index of the section that content will be appended to.
function LuaDocument:appendContent() end

---Copy a field without overwriting destination fields.
---@param sourceName string The source field name.
---@param targetName string The target field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The new fields.
function LuaDocument:copyFieldNoOverwrite() end

---Get number of a field.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return integer # The number of the field.
function LuaDocument:countField() end

---Delete fields.
---@param name string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@overload fun(name: string, value: string, caseSensitive?: boolean)
function LuaDocument:deleteField() end

---Get the content.
---@param number? integer The index of the section to retrieve.
---@return string # The content.
function LuaDocument:getContent() end

---Get all fields names.
---@return string ... # The fields names.
function LuaDocument:getFieldNames() end

---Set a field value.
---@param name string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return string? # The field value.
function LuaDocument:getFieldValue() end

---Get field values.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return string ... # The field values.
function LuaDocument:getFieldValues() end

---Get next document section.
---@return LuaDocumentSection? # The next section.
function LuaDocument:getNextSection() end

---Get the document reference.
---@return string # The reference.
function LuaDocument:getReference() end

---Get the section by index from zero.
---@param number integer The section number.
---@return LuaDocumentSection? # The section.
function LuaDocument:getSection() end

---Get the number of sections in the document.
---@return integer # The number of sections in the document.
function LuaDocument:getSectionCount() end

---Return if field exists.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return boolean # Field exists.
function LuaDocument:hasField() end

---Add a field from XML.
---@param node LuaXmlNode The XML.
---@param name? string The field name. (default: )
---@return LuaField? # The new field.
function LuaDocument:insertXml() end

---Add fields from XML.
---@param node LuaXmlNode The XML.
function LuaDocument:insertXmlWithoutRoot() end

---Remove the specified section by index from zero.
---@param number integer The index of the section to remove.
function LuaDocument:removeSection() end

---Rename a field.
---@param oldName string The old field name.
---@param newName string The new field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The new fields.
function LuaDocument:renameField() end

---Set the content.
---@param content string The new content.
---@param number? integer The index of the section to assign.
function LuaDocument:setContent() end

---Set a field value.
---@param name string The field name.
---@param Value string The new value.
function LuaDocument:setFieldValue() end

---Set the document reference.
---@param reference string The reference.
function LuaDocument:setReference() end

---Write in IDX format to a string.
---@return string # The document idx as string
function LuaDocument:to_idx() end

---Write in JSON format to a string.
---@return string # The document json as string
function LuaDocument:to_json() end

---Write in XML format to a string.
---@return string # The document xml as string
function LuaDocument:to_xml() end

---Write in IDX format to file.
---@param filename string The output filename.
---@return boolean # Indicates success.
function LuaDocument:writeStubIdx() end
function LuaDocument:write_idx() end

---Write in JSON format to file.
---@param filename string The output filename.
---@return boolean # Indicates success.
function LuaDocument:write_json() end

---Write in XML format to file.
---@param filename string The output filename.
---@return boolean # Indicates success.
function LuaDocument:writeStubXml() end
function LuaDocument:write_xml() end

---Document section class
---@class LuaDocumentSection : LuaDocument
local LuaDocumentSection = {}

---Document Field class
---@class LuaField : LuaFieldContainer
local LuaField = {}

---Add a field.
---@param name string The field name.
---@param value string The field value.
---@return LuaField? # The new field.
---@overload fun(field: LuaField, name?: string): LuaField?
function LuaField:addField() end

---Copy a field without overwriting destination fields.
---@param sourceName string The source field name.
---@param targetName string The target field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The new fields.
function LuaField:copyFieldNoOverwrite() end

---Get number of a field.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return integer # The number of the field.
function LuaField:countField() end

---Delete an attribute.
---@param name string The attribute name.
function LuaField:deleteAttribute() end

---Delete fields.
---@param name string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@overload fun(name: string, value: string, caseSensitive?: boolean)
function LuaField:deleteField() end

---Delete this fields.
function LuaField:deleteThisField() end

---Get an attribute value.
---@param name string The attribute name.
---@return string # The attribute value.
function LuaField:getAttributeValue() end

---Get all fields names.
---@return string ... # The fields names.
function LuaField:getFieldNames() end

---Get field values.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return string ... # The field values.
function LuaField:getFieldValues() end

---Return whether an attribute exists.
---@param name string The attribute name.
---@return boolean # attribute exists.
function LuaField:hasAttribute() end

---Return if field exists.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return boolean # Field exists.
function LuaField:hasField() end

---Add a field from XML.
---@param node LuaXmlNode The XML.
---@param name? string The field name. (default: )
---@return LuaField? # The new field.
function LuaField:insertXml() end

---Add fields from XML.
---@param node LuaXmlNode The XML.
function LuaField:insertXmlWithoutRoot() end

---Get the name of the field.
---@return string # The name of the field.
function LuaField:name() end

---Rename a field.
---@param oldName string The old field name.
---@param newName string The new field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The new fields.
function LuaField:renameField() end

---Set an attribute value.
---@param name string The attribute name.
---@param value string The attribute value.
function LuaField:setAttributeValue() end

---Set the value of the field.
---@param value string The value.
function LuaField:setValue() end

---Get the value of the field.
---@return string # The value of the field.
function LuaField:value() end

---Document field container class.
---@class LuaFieldContainer
local LuaFieldContainer = {}

---Copy a field.
---@param sourceName string The source field name.
---@param targetName string The target field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The new fields.
function LuaFieldContainer:copyField() end

---Remove all instances of field with the given path.
---@param path string The path to the field to be removed.
function LuaFieldContainer:deleteFieldByPath() end

---Get a field by name.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField # The field.
function LuaFieldContainer:getField() end

---Get fields by name.
---@param fieldName string The field name.
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The fields.
function LuaFieldContainer:getFields() end

---Get fields whose names/paths match a regex.
---@param fieldRegex string The regex that should be applied to field names/paths.
---@param recursive? boolean Should the regex be recursively applied to subfields (default: true)
---@param matchFullPath? boolean Should the regex be applied to the full path to the field (default: true)
---@param caseSensitive? boolean Case-sensitivity. (default: true)
---@return LuaField ... # The fields.
function LuaFieldContainer:getFieldsByRegex() end

---Get the value of the first instance of a field/attribute that exists/contains a value by path.
---@param path string The path to the field/attribute.
---@return string? # The value. (empty string if no value found)
function LuaFieldContainer:getValueByPath() end

---Get field/attributes values by path.
---@param path string The path to the field/attribute.
---@return string ... # The values.
function LuaFieldContainer:getValuesByPath() end

---Add fields from JSON.
---@param json LuaJsonObject The json
---@param name? string The field name. (default: )
---@overload fun(json: LuaJsonArray, name: string)
---@overload fun(json: string, name?: string)
function LuaFieldContainer:insertJson() end

---HTTP Request class
---@class LuaHttpRequest
local LuaHttpRequest = {}

---Constructor for LuaHttpRequest
---@param config LuaConfig The config object
---@param section string The section containing settings for HTTP request
---@overload fun()
---@return LuaHttpRequest
function LuaHttpRequest.new(config, section) end

---Send the request
---@return LuaHttpResponse # The response
function LuaHttpRequest:send() end

---Set the body of the request
---@param body? string The body of the request
function LuaHttpRequest:set_body() end

---Set configuration for request
---@param config LuaConfig The config object
---@param section string The section containing settings for HTTP request
function LuaHttpRequest:set_config() end

---Add a header to the request
---@param name string The header name
---@param value? string The header value
function LuaHttpRequest:set_header() end

---Add headers to the request
---@param headers table<string, string> The header name
function LuaHttpRequest:set_headers() end

---Set the HTTP method
---@param method string The HTTP method
function LuaHttpRequest:set_method() end

---Set the URL
---@param url string The URL
function LuaHttpRequest:set_url() end

---HTTP Response class
---@class LuaHttpResponse
local LuaHttpResponse = {}

---Get the body
---@return string # The body as a string
function LuaHttpResponse:get_body() end

---Get a response header value
---@param name string The header name
---@return string? # The response header value
function LuaHttpResponse:get_header() end

---Get all the response headers
---@return table<string, string> # The response headers
function LuaHttpResponse:get_headers() end

---Get the HTTP result code
---@return integer # The HTTP result code
function LuaHttpResponse:get_http_code() end

---JSON array class
---@class LuaJsonArray : LuaJsonBase
local LuaJsonArray = {}

---Constructor for JsonArray.
---@param values lua_json_value_type ... The value to append to the JSON array
---@return LuaJsonArray
function LuaJsonArray.new(values) end

---Append a value to the JSON array
---@param values lua_json_value_type ... The value to append to the JSON array
function LuaJsonArray:append() end

---Clear the JSON array
function LuaJsonArray:clear() end

---Copy the JSON value
---@return LuaJsonArray # The JSON value copy
function LuaJsonArray:copy() end

---Determine whether JSON array is empty
---@return boolean # True if JSON array is empty
function LuaJsonArray:empty() end

---Use with for loop to iterate over all values
---@return json_array_ipairs_next_function # next function
---@return LuaJsonArray # this
function LuaJsonArray:ipairs() end

---Determine the size of the JSON array
---@return long long # The size of the JSON array
function LuaJsonArray:size() end

---Base class of JSON types
---@class LuaJsonBase
local LuaJsonBase = {}

---Determine whether the path exists
---@param pathElements json_path_string_or_integer ... Path elements of object attribute names or array indexes
---@return boolean # True if the path exists
function LuaJsonBase:exists() end

---Determine whether the path exists
---@param path string Slash separated path of object attribute names or array indexes
---@return boolean # True if the path exists
function LuaJsonBase:existsByPath() end

---Return true if array value
---@return boolean # True if array value
function LuaJsonBase:is_array() end

---Return true if boolean value
---@return boolean # True if boolean value
function LuaJsonBase:is_boolean() end

---Return true if floating point value
---@return boolean # True if floating point value
function LuaJsonBase:is_float() end

---Return true if integral value
---@return boolean # True if integral value
function LuaJsonBase:is_integer() end

---Return true if null value
---@return boolean # True if null value
function LuaJsonBase:is_null() end

---Return true if numeric value
---@return boolean # True if numeric value
function LuaJsonBase:is_number() end

---Return true if object value
---@return boolean # True if object value
function LuaJsonBase:is_object() end

---Return true if simple value (boolean, integer, float or string)
---@return boolean # True if simple value
function LuaJsonBase:is_simple_value() end

---Return true if string value
---@return boolean # True if string value
function LuaJsonBase:is_string() end

---Lookup the JSON value using path from current value if the path exists
---@param pathElements json_path_string_or_integer ... Path elements of object attribute names or array indexes
---@return LuaJsonValue? # The JSON value if the path exists
function LuaJsonBase:lookup() end

---Lookup the JSON value using path from current value if the path exists
---@param path string Slash separated path of object attribute names or array indexes
---@return LuaJsonValue? # The JSON value if the path exists
function LuaJsonBase:lookupByPath() end

---Get the JSON value as a string
---@return string? # The JSON value as a string
function LuaJsonBase:string() end

---JSON object class
---@class LuaJsonObject : LuaJsonBase
local LuaJsonObject = {}

---Constructor for JsonObject.
---@param attributes lua_json_object_type The table of attributes to be assigned
---@overload fun()
---@return LuaJsonObject
function LuaJsonObject.new(attributes) end

---Assign an attribute or attributes on the JSON object
---@param name string The name of the attribute to be assigned
---@param value lua_json_value_type The value of the attribute to be assigned
---@overload fun(attributes: lua_json_object_type)
function LuaJsonObject:assign() end

---Clear the JSON object
function LuaJsonObject:clear() end

---Copy the JSON value
---@return LuaJsonObject # The JSON value copy
function LuaJsonObject:copy() end

---Determine whether JSON object has attributes
---@return boolean # True if JSON object has no attributes
function LuaJsonObject:empty() end

---Erase a specific attribute from the JSON object
---@param name string ... The name of the attribute that will be erased
function LuaJsonObject:erase() end

---Use with for loop to iterate over all attributes
---@return json_object_pairs_next_function # next function
---@return LuaJsonObject # this
function LuaJsonObject:pairs() end

---Determine the number of attributes in the JSON object
---@return long long # The number of attributes in the JSON object
function LuaJsonObject:size() end

---JSON value class
---@class LuaJsonValue : LuaJsonBase
local LuaJsonValue = {}

---Constructor for JsonValue.
---@param value lua_json_type The initial value
---@return LuaJsonValue
function LuaJsonValue.new(value) end

---Get the JSON array for the current value if it is an array
---@return LuaJsonArray? # The JSON array if the value is an array
function LuaJsonValue:array() end

---Copy the JSON value
---@return LuaJsonValue # The JSON value copy
function LuaJsonValue:copy() end

---Get the JSON object for the current value if it is an object
---@return LuaJsonObject? # The JSON object if the value is an object
function LuaJsonValue:object() end

---Get the value if the JSON value is a simple type
---@return lua_json_simple_type # The value if the JSON value is a simple type
---@overload fun(def: lua_json_simple_type): lua_json_simple_type
function LuaJsonValue:value() end

---Logging class
---@class LuaLog
local LuaLog = {}

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:always() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:critical() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:error() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:full() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:normal() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param data any ... This is the message you want to log out.
function LuaLog:warning() end

---Log out a string! At the moment if you have other types, you have to convert them yourself.
---@param level integer Log messages need an attached log level. It is expected that you will normally want to use one of the predefined functions log_level_(full/error/always/...) here.
---@param data any ... This is the message you want to log out.
function LuaLog:write_line() end

---Logging service class
---@class LuaLogService
local LuaLogService = {}

---Construct a LuaLogService
---@param config LuaConfig The config object from which the log should be read.
---@return LuaLogService
function LuaLogService.new(config) end

---Get the log object for a log type
---@param type string The log type name
---@return LuaLog # The log object.
function LuaLogService:get_log() end

---Regular expression match class
---@class LuaRegexMatch
local LuaRegexMatch = {}

---Return the length of the sub match.
---@param sub? integer The sub match number. A value of zero refers to the full match. (default: 0)
---@return integer # The length of the sub match.
function LuaRegexMatch:length() end

---Returns the next regex match object for the string.
---@return LuaRegexMatch? # The next regex match object for the string.
function LuaRegexMatch:next() end

---Return the position of the sub match in the string as an index from 1.
---@param sub? integer The sub match number. A value of zero refers to the full match. (default: 0)
---@return integer # The position of the sub match.
function LuaRegexMatch:position() end

---Returns the number of sub matches for the current match, including the full match.
---@return integer # The number of sub matches.
function LuaRegexMatch:size() end

---Return the string for the sub match.
---@param sub? integer The sub match number. A value of zero refers to the full match. (default: 0)
---@return string # The string for the sub match.
function LuaRegexMatch:str() end

---XML attribute class
---@class LuaXmlAttribute
local LuaXmlAttribute = {}

---Return the name of the attribute.
---@return string # The name of the attribute.
function LuaXmlAttribute:name() end

---Return the next attribute.
---@return LuaXmlAttribute? # The next attribute.
function LuaXmlAttribute:next() end

---Return the previous of the attribute.
---@return LuaXmlAttribute? # The previous attribute.
function LuaXmlAttribute:prev() end
function LuaXmlAttribute:previous() end

---Return the value of the attribute.
---@return string # The value of the attribute.
function LuaXmlAttribute:value() end

---XML document class
---@class LuaXmlDocument
local LuaXmlDocument = {}

---Execute an XPath query for a node set.
---@param xpath string The XPath query.
---@param context? LuaXmlNode The XPath context node.
---@return LuaXmlNodeSet # The result node set.
function LuaXmlDocument:XPathExecute() end

---Register an XPath namespace.
---@param prefix string The namespace prefix.
---@param uri string The namespace URI.
---@return boolean # Indicates success.
function LuaXmlDocument:XPathRegisterNs() end

---Execute an XPath query for a single string.
---@param xpath string The XPath query.
---@param context? LuaXmlNode The XPath context node.
---@return string? # The resulting string.
function LuaXmlDocument:XPathValue() end

---Execute an XPath query for strings.
---@param xpath string The XPath query.
---@param context? LuaXmlNode The XPath context node.
---@return string ... # The resulting strings.
function LuaXmlDocument:XPathValues() end

---Return the root node of the document.
---@return LuaXmlNode # The root node.
function LuaXmlDocument:root() end

---XML node class
---@class LuaXmlNode
local LuaXmlNode = {}

---Return the first or named attribute.
---@param name? string The name of the attribute. (default: )
---@return LuaXmlAttribute? # The first or named attribute.
function LuaXmlNode:attr() end
function LuaXmlNode:attribute() end

---Return the content of the node.
---@return string # The content of the node.
function LuaXmlNode:content() end

---Return the first child node.
---@return LuaXmlNode? # The first child node.
function LuaXmlNode:firstChild() end
function LuaXmlNode:first_child() end

---Return the last child node.
---@return LuaXmlNode? # The last child node.
function LuaXmlNode:lastChild() end
function LuaXmlNode:last_child() end

---Return the name of the node.
---@return string # The name of the node.
function LuaXmlNode:name() end

---Return the next node.
---@return LuaXmlNode? # The next node.
function LuaXmlNode:next() end

---Return the path of the node.
---@return string # The path of the node.
function LuaXmlNode:nodePath() end
function LuaXmlNode:node_path() end

---Return the parent node.
---@return LuaXmlNode? # The parent node.
function LuaXmlNode:parent() end

---Return the previous node.
---@return LuaXmlNode? # The previous node.
function LuaXmlNode:prev() end
function LuaXmlNode:previous() end

---Return the type of the node.
---@return string # The type of the node.
function LuaXmlNode:type() end

---XML node set class
---@class LuaXmlNodeSet
local LuaXmlNodeSet = {}

---Return the node at a particular index.
---@param index integer The index of the node in the set.
---@return LuaXmlNode? # The node.
function LuaXmlNodeSet:at() end

---Use with for loop to iterate over all nodes
---@return xml_node_set_ipairs_next_function # next function
---@return LuaXmlNodeSet # this
function LuaXmlNodeSet:ipairs() end

---Return the size of the node set.
---@return integer # The size of the node set.
function LuaXmlNodeSet:size() end

-- Global functions ------------------------------------------

---Return the absolute form of a path.
---@param path string The input path.
---@return string # The absolute path.
function abs_path() end

---Base64 decode some data.
---@param data string The input string to be base64 decoded.
---@return string? # The unencoded string.
function base64_decode() end

---Base64 encode some data.
---@param data string The input string to be base64 encoded.
---@return string # The base64 encoded string.
function base64_encode() end

---Convert a date string from one format to another.
---@param date_string string The date string to convert. The input string is interpreted as in the local timezone unless it is outside the epoch range (1970 - 2038) in which case it is GMT. Any explicit timezone information overrides this.
---@param input_formats string The possible date formats of the input as a comma separated list.
---@param output_format string The date format to output.
---@param output_gmt? boolean Produce the output string in GMT rather than local timezone (default: false)
---@return string # Converted date string.
function convert_date_time() end

---Convert a string between encodings.
---@param data string The input string to convert encoding.
---@param output_encoding string The output encoding.
---@param unicode_table_directory? string The unicode table directory. Can be nil. (default: )
---@param input_encoding? string The encoding of the input string. (default: UTF8)
---@return string # The input string in the output encoding.
function convert_encoding() end

---Copy a file.
---@param src string The source file to copy.
---@param dest string The destination location.
---@param overwrite? boolean Overwrite the destination file if it exists. (default: true)
---@return boolean # Indicate whether the file was copied.
function copy_file() end

---Create a path on the filesystem.
---@param path string The path to create.
---@return string? # The path is returned if it was created successfully.
function create_path() end

---Generate a UUID.
---@return string # UUID
function create_uuid() end

---Get the current date time in the specified format.
---@param format string The date format to output as
---@param gmt? boolean Produce the output string in GMT rather than local timezone (default: false)
---@return string # The resulting date string.
function date_time_now() end

---Basic decryption of a string.
---@param data string The data to decrypt.
---@return string # The decrypted data.
function decrypt() end

---Decrypt and return the value of a security field.
---@param acl string The encrypted value of the security field.
---@param regexList string ... List of regexes to capture in the ACL.
---@return string? # The value of the security field
function decrypt_security_field() end

---Delete a file.
---@param filename string The file to delete.
---@return boolean # Indicate whether the file was deleted.
function delete_file() end

---Delete an empty directory.
---@param path string The directory to delete.
---@return boolean # Indicate whether the directory was deleted.
function delete_path() end

---Basic encryption of a string.
---@param data string The data to encrypt.
---@return string # The encrypted data.
function encrypt() end

---Encrypt and return the value of a security field.
---@param acl string The value of the security field.
---@param regexList string ... List of regexes to capture in the ACL.
---@return string? # The encrypted security field value
function encrypt_security_field() end

---Extract a date form a string passed in along with date formats to match.
---@param data string The input string.
---@param input_formats string The possible date formats of the input as a comma separated list.
---@param output_format string The date format to output as
---@return string # The resulting date string.
function extract_date() end

---Set the date properties of a file.
---@param filename string The filename.
---@param creation_date? string The creation date. Can be nil. (default: )
---@param modified_date? string The modified date. Can be nil. (default: )
---@param accessed_date? string The accessed date. Can be nil. (default: )
---@param date_format? string The format of the date parameters. (default: EPOCHSECONDS)
---@return boolean # Indicates whether the dates were set successfully.
function file_setdates() end
function file_set_dates() end

---Generate fingerprints for a string
---@param data string The string to fingerprint
---@param min_chars? integer Absolute minimum chunk size in UTF8 characters. (default: 10)
---@param mask_size? integer Size of bitmask when calculating string chunk boundaries. Valid range 1-31. Smaller values increase number of fingerprints. (default: 8)
---@param num_bytes? integer Length of substring to check when calculating string chunk boundaries. (default: 48)
---@return string ... # Fingerprints for the input data
function fingerprint_string() end

---Get the config object from a file.
---@param filename string The config filename.
---@return LuaConfig # The config object.
function get_config() end

---Retrieve the current working directory.
---@return string # The current working directory.
function getcwd() end
function get_cwd() end

---Get a log service object
---@param config LuaConfig The config object
---@return LuaLogService # The log service object
function get_log_service() end

---Replace consecutive whitepace characters with a single space in the input string and return the result.
---@param data? string The input string.
---@return string # The resulting string with reduced whitespace.
function gobble_whitespace() end

---Returns SHA1, SHA256, or MD5 hash of a file.
---@param filename string The name of the file to be hashed.
---@param algorithms string ... The algorithm names; either "SHA1", "SHA256", or "MD5".
---@return string ... # SHA1, SHA256, or MD5 hashes.
---@overload fun(getNextBytes: hash_file_bytes_function, algorithms: string ...): string
function hash_file() end

---Returns SHA1, SHA256, or MD5 hash of some text.
---@param text string The text to be hashed.
---@param algorithm? string The algorithm name; either "SHA1", "SHA256", or "MD5". (default: MD5)
---@return string? # SHA1, SHA256, or MD5 hash.
function hash_string() end

---Determine whether a path refers to a directory.
---@param path string The path to check.
---@return boolean # Indicate whether the path is a directory.
function is_dir() end
function is_directory() end

---NOTE: overly-simplistic and DEPRECATED (in favour of get_log(config, section)) for anything more than trivial logging. Write a log message to a file.
---@param filename string The log filename.
---@param message any ... The log message.
function log() end

---Gets the predefined always log level from the pseudo-enumeration.
---@return integer
function log_level_always() end

---Gets the predefined critical log level from the pseudo-enumeration.
---@return integer
function log_level_critical() end

---Gets the predefined error log level from the pseudo-enumeration.
---@return integer
function log_level_error() end

---Gets the predefined full log level from the pseudo-enumeration.
---@return integer
function log_level_full() end

---Gets the predefined normal log level from the pseudo-enumeration.
---@return integer
function log_level_normal() end

---Gets the predefined warning log level from the pseudo-enumeration.
---@return integer
function log_level_warning() end

---Return the lower case version of a utf-8 string.
---@param input string The original string.
---@return string # The original string in lower case.
function lower_case_utf8() end

---Move a file.
---@param src string The source file to move.
---@param dest string The destination location.
---@param overwrite? boolean Overwrite the destination file if it exists. (default: true)
---@return boolean # Indicate whether the file was moved.
function move_file() end

---Extract values from a single character delimited list.
---@param csv string The input delimited list.
---@param parse_quotes? boolean Parse quotes around values. (default: true)
---@return string ... # The values extracted from the delimited list.
---@overload fun(csv: string, delimiter?: string, parse_quotes?: boolean): string
function parse_csv() end

---Call a function on each parsed document from CSV file
---@param filename string The filename of the csv format file
---@param handler document_handler_function Handler function to call on each document
---@param params parse_document_csv_named_parameters
function parse_document_csv() end

---Return a LuaDocument constructed from IDX, or call a function on each parsed document
---@param filename string The input filename
---@param handler document_handler_function Handler function to call on each document
---@return LuaDocument? # The constructed document
---@overload fun(input: string, file: boolean, handler: document_handler_function): LuaDocument?
---@overload fun(input: string, file?: boolean): LuaDocument?
function parse_document_idx() end

---Call a function on each parsed document from XML file
---@param filename string The filename of the xml file
---@param handler document_handler_function Handler function to call on each document
---@param params parse_document_xml_named_parameters
---@return LuaDocument? # The constructed document
---@overload fun(input: string, file: boolean, handler: document_handler_function, params: parse_document_xml_named_parameters): LuaDocument?
---@overload fun(input: string, file?: boolean, params: parse_document_xml_named_parameters): LuaDocument?
function parse_document_xml() end

---Parse a JSON string and return a JSON value.
---@param json string The input JSON string to parse.
---@return LuaJsonValue? # The JSON value.
function parse_json() end

---Parse a JSON array string and return a JSON array.
---@param json string The input JSON array string to parse.
---@return LuaJsonArray? # The JSON array.
function parse_json_array() end

---Parse a JSON object string and return a JSON object.
---@param json string The input JSON object string to parse.
---@return LuaJsonObject? # The JSON object.
function parse_json_object() end

---Parse an XML string and return an XML document object.
---@param xml string The input XML string to parse.
---@return LuaXmlDocument? # The XML document.
function parse_xml() end

---Returns the strength of the input password (less than 2 is weak, 2-4 is acceptable, 5 or more is strong).
---@param password string The password.
---@return integer # The strength of the input password (1-10).
function password_strength() end

---Check for a regex match on a string.
---@param data string The string to match against.
---@param regex string The regex to match.
---@param case_sensitive? boolean Case sensitivity. (default: true)
---@return string ... # The full match or sub matches.
function regex_match() end

---Replace all matches for a specified regex in a string.
---@param data string The string to replace within.
---@param regex string The regex to match against.
---@param replacement string The description of how to replace matches.
---@return string # The original data string with all instances of the regex replaced.
function regex_replace() end
function regex_replace_all() end

---Search for regex matches in a string.
---@param data string The string to search within.
---@param regex string The regex to search for.
---@param case_sensitive? boolean Case sensitivity. (default: true)
---@return LuaRegexMatch? # Object wrapping the first match with access to all following matches.
function regex_search() end

---Returns the absolute path of the script that called this function
---@return string ... # The script directory, and the script filename
function script_path() end

---Send an ACI command.
---@param host string ACI server hostname.
---@param port unsigned short ACI server port number.
---@param action string Action name.
---@param params? table<string, string> Action parameters. (default: )
---@param timeout? integer Timeout in milliseconds. (default: 3000)
---@param retries? integer Number of connection retries. (default: 3)
---@param ssl_params? table<string, string> SSL parameters. (default: )
---@return string? # Result of the ACI command.
function send_aci_action() end

---Send an ACI command.
---@param host string ACI server hostname.
---@param port unsigned short ACI server port number.
---@param action string Action string including parameters.
---@param timeout? integer Timeout in milliseconds. (default: 3000)
---@param retries? integer Number of connection retries. (default: 3)
---@param ssl_params? table<string, string> SSL parameters. (default: )
---@return string? # Result of the ACI command.
function send_aci_command() end

---Send an asynchronous ACI command, but wait for it to finish.
---@param host string ACI server hostname.
---@param port unsigned short ACI server port number.
---@param action string Action name.
---@param params? table<string, string> Action parameters. (default: )
---@param timeoutMilliseconds? integer Timeout in milliseconds. (default: 60000)
---@param connectionRetries? integer Number of connection retries. (default: 3)
---@param ssl_params? table<string, string> SSL parameters. (default: )
---@return string? # queueinfo getstatus result of the ACI command.
function send_and_wait_for_async_aci_action() end

---Send an http request.
---@param params send_http_request_named_parameters
---@return string # The http response.
function send_http_request() end

---Sleep for a number of milliseconds.
---@param ms integer Duration to sleep for in milliseconds
function sleep() end

---Decompress a zip file to a directory.
---@param path string The zip file to decompress.
---@param dest string The path where the compressed files will be extracted.
---@return boolean # Indicate whether the operation was successful.
function unzip_file() end

---Return the upper case version of a utf-8 string.
---@param input string The original string.
---@return string # The original string in upper case.
function upper_case_utf8() end

---URL escape some text.
---@param url string The URL to escape.
---@return string # The escaped text.
function url_escape() end
function escape_url() end

---Unescape some URL escaped text.
---@param urlescaped string The URL escaped text to unescape.
---@return string # The unescaped text.
function url_unescape() end
function unescape_url() end

---Decode an XML string.
---@param data string The input string to be XML decoded.
---@return string # The decoded string.
function xml_decode() end

---Encode a string for use in XML.
---@param data string The input string to be XML encoded.
---@return string # The XML encoded string.
function xml_encode() end

---List the contents of a zip file
---@param zipfile string The zip file to extract a file from
---@param file string The file path within the zip
---@param dest string The destination filename
---@return boolean # Indicate whether the operation was successful.
function zip_extract() end

---Compress a file or directory to a zip file in the containing directory.
---@param path string The file or directory to compress.
---@param overwrite? boolean Overwrite the zip file if it exists. (default: false)
---@return boolean # Indicate whether the operation was successful.
function zip_file() end

---List the contents of a zip file
---@param zipfile string The zip file to inspect
---@return string ... # File paths contained in the zip
function zip_list() end

