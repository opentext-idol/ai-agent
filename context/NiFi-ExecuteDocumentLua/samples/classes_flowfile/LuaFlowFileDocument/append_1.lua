--[[{
    "name": "Appending new parts to a FlowFile document"
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

    -- Adds a content part and appends replacement XML metadata
    ffdocument:append(function(action)
            action:addContent("Hello world")
            action:getXmlMetadata():addChild("said_hello"):setValue("true")
        end)

end