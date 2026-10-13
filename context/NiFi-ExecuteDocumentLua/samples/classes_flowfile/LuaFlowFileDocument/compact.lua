--[[{
    "name": "Stripping parts marked for removal from a FlowFile document"
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

    local deleteParts = function(action)
        action:deletePart()
    end
    
    -- Mark all files for removal in the FlowFile document
    ffdocument:append({
        onContentFile = deleteParts,
        onContentFilename = deleteParts})
    
    -- Remove parts marked for removal
    ffdocument:compact()
    
    -- note: calling append and then compact is equivalent to just calling modify

end