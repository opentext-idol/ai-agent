--[[{
    "name": "Building XML metadata from multiple parts"
}]]

function handler(ffdocument, session)

    local metadata = nil
    local contentPageCount = 0

    ffdocument:modify({
        preAction = function(action)
            metadata = action:getXmlMetadata()
        end,
        onContent = function(action)
            action:readContent(
                function(inputstream)
                    contentPageCount = contentPageCount + 1
                end)
        end,
        onContentFile = function(action)
            metadata:addChild("FILE_PART_ID"):setValue(action:getPartId())
        end,
        onContentFilename = function(action)
            metadata:addChild("FILENAME_PART_ID"):setValue(action:getPartId())
        end,
        postAction = function(action)
            metadata:addChild("CONTENT_PAGE_COUNT"):setValue(tostring(contentPageCount))
        end})

end