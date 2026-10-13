--[[{
    "name": "Calculating hash of each file in a FlowFile document"
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

    local hashFieldFromInputStream = function(inputstream, xmlmetadata)
        local hash = hash_file(
            function()
                return inputstream:read(4096)
            end,
            "MD5")
        xmlmetadata:addChild("MD5HASH"):setValue(hash)
    end

    ffdocument:append({
        onContentFile = function(action)
            action:readFile(
                function(inputstream)
                    hashFieldFromInputStream(inputstream, action:getPartXmlMetadata())
                end)
        end,
        onContentFilename = function(action)
            local inputstream = new LuaInputStream(action:getFilename())
            hashFieldFromInputStream(inputstream, action:getPartXmlMetadata())
        end})

end