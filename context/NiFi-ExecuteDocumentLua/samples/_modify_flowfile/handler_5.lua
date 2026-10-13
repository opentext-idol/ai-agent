--[[{
    "name": "Parse XML from the content file(name), and return new documents"
}]]

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