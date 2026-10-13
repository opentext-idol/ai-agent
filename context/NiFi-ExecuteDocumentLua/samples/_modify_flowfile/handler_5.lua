--[[{
    "name": "Parse XML from the content file(name), and return new documents"
}]]

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

function handler(ffdocument, session)
    -- Modify the xmlParams values to match your XML
    local xmlParams = {
        document_root_paths={"documents/document"},
        reference_paths={"reference"},
        content_paths={"content"}
    }
    
    local myDocuments = {}
    
    local parseXml = function(input, isFile)
        parse_document_xml(
            input,
            isFile,
            function(document)
                table.insert(myDocuments, document) 
            end,
            xmlParams)
    end
    
    ffdocument:read({
        onContentFile = function(file)
            file:readFile(
                function(inputstream)
                    pcall(parseXml, inputstream:read('a'), false)
                end)
        end,
        onContentFilename = function(file)
            pcall(parseXml, file:getFilename(), true)
        end})
    
    return table.unpack(myDocuments)
end