--[[{
    "name": "Getting and setting attributes on a FlowFile"
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

    local reference = ffdocument:getReference()             -- idol.reference
    local referenceAction = ffdocument:getReferenceAction() -- idol.reference.action

    local state = ffdocument:getAttribute("luahandlerstate")
    
    if state ~= "done" then
        
        ffdocument:setAttributes( { luahandlerstate = "done" } )
        
    end

end