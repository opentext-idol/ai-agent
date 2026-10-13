--[[{
    "name": "Modifying parts in a FlowFile document"
}]]

function handler(ffdocument, session)

    local allContent = ""
    ffdocument:modify({
        -- preAction = function(action) do_nothing end,
        onContent = function(action)
            action:readContent(function(inputstream)
                    allContent = allContent .. "\012" .. inputstream:read("a")
                end)
        end,
        
        onContentFile = function(action)
            action:writeFile(function(outputstream)
                    outputstream:write("This file content has been overwritten")
                end)
        end,
        
        onContentFilename = function(action)
            action:transferFilenameToFile()
        end,
        
        postAction = function(action)
            action:getXmlMetadata():addChild("CONTENT_MD5"):setValue(hash_string(allContent))
        end})

end