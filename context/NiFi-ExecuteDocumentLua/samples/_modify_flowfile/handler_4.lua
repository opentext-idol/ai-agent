--[[{
    "name": "Building XML metadata from multiple parts"
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