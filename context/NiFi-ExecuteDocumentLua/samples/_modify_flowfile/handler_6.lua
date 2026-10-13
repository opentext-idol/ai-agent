--[[{
    "name": "Handling all types of file part"
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