--[[{
    "name": "Modifying parts in a FlowFile document"
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