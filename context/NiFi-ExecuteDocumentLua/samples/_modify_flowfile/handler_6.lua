--[[{
    "name": "Handling all types of file part"
}]]

function handler(ffdocument, session)

    local metadata = nil

    ffdocument:modify({
        preAction = function(action)
            metadata = action:getXmlMetadata()
        end,
        
        -- Explicitly handle embedded File parts
        onContentFile = function(action)
            metadata:addChild("FILE_PART_ID"):setValue(action:getPartId())
        end,
        
        -- Default action for onContentFile, onContentFile and onExternalFile if not explicitly set
        defaultFileAction = function(action)
            metadata:addChild("OTHERFILE_PART_ID"):setValue(action:getPartId())
        end})

end