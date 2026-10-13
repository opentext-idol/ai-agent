--[[{
    "name": "Reading parts in a FlowFile document"
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

    local hashes = {}
    ffdocument:read({
        -- preAction = function(action) do_nothing end,
        onContent = function(action)
            action:readContent(function(inputstream)
                    local pageContent = inputstream:read("a")
                    hashes:insert(hash_string(pageContent))
                end)
        end,
        
        onContentFile = function(action)
            action:readFile(function(inputstream)
                    local fileContent = inputstream:read("a")
                    hashes:insert(hash_string(fileContent))
                end)
        end,
        
        onContentFilename = function(action)
            local f = assert(io.open(action:getFilename()))
            local fileContent = f:read("a")
            f:close()
            hashes:insert(hash_string(fileContent))
        end
        --, postAction = function(action) do_nothing end
        })

end