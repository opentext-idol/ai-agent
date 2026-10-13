--[[{
    "name": "Appending new parts to replace existing parts in a FlowFile document"
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

    ffdocument:append({
        -- preAction = function(action) do_nothing end,
        -- onContent = function(action) do_nothing end,
        onContentFile = function(action)
            action:writeFile(function(outputstream)
                    outputstream:write("This file content has been overwritten")
                end)
        end,
        
        onContentFilename = function(action)
            action:deletePart()
        end
        --, postAction = function(action) do_nothing end
        })

end